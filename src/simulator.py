"""Monte-Carlo single-link-failure simulator.

For every trial:
  1. Pick one link uniformly from ``E`` to fail.
  2. For every (s,d) pair, walk the primary path used by ``s`` to reach
     ``d``. If that path does not traverse the failed link, the pair
     is delivered. If it does:
       a. If the failure-detecting node has another MNP-e/LFC next-hop
          for ``d`` in its next-hop set, the pair is recovered.
       b. Else, if the broken link is in the protected set (BPP /
          TA-BPP), the pair is recovered via the pre-computed tunnel.
       c. Otherwise the pair is lost.

We report:
  - ``topological_availability`` = successful (s,d) deliveries / total
  - ``traffic_availability``      = delivered traffic / total traffic
  - ``packet_loss_proxy``        = 1 - topological_availability
  - ``recovery_count``           = number of (s,d) recoveries triggered
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set, Tuple

import networkx as nx

from .path_construction import build_primary_paths, detect_failure_point
from .shortest_path import dijkstra, reconstruct_path, shortest_path
from .utils import normalize_edge


@dataclass
class SimulationOutcome:
    topological_availability: float = 0.0
    traffic_availability: float = 0.0
    packet_loss_proxy: float = 0.0
    recovery_count: int = 0
    bpp_recovery_count: int = 0
    mnp_recovery_count: int = 0
    capacity_drop_count: int = 0
    max_link_utilization: float = 0.0
    num_trials: int = 0

    def as_dict(self) -> Dict:
        return {
            "topological_availability": self.topological_availability,
            "traffic_availability": self.traffic_availability,
            "packet_loss_proxy": self.packet_loss_proxy,
            "recovery_count": self.recovery_count,
            "bpp_recovery_count": self.bpp_recovery_count,
            "mnp_recovery_count": self.mnp_recovery_count,
            "capacity_drop_count": self.capacity_drop_count,
            "max_link_utilization": self.max_link_utilization,
            "num_trials": self.num_trials,
        }


def _protected_set(protected_links: Sequence[Tuple[int, int]]) -> Set[Tuple[int, int]]:
    return {normalize_edge(*e) for e in protected_links}


def simulate_failures(
    graph: nx.Graph,
    next_hops_per_c: Dict[int, Dict[int, Set]],
    protected_links: Sequence[Tuple[int, int]],
    traffic: Optional[Dict[Tuple[int, int], float]] = None,
    num_trials: int = 300,
    seed: Optional[int] = None,
    failure_sampling: str = "probability_weighted",
    enforce_capacity: bool = True,
    drop_model: str = "bottleneck",
) -> SimulationOutcome:
    """Run the Monte-Carlo single-link-failure experiment with dynamic capacity enforcement.

    Parameters
    ----------
    graph
        NetworkX graph with edge costs, optional capacities, and failure probabilities.
    next_hops_per_c
        MNP-e / LFC next-hop sets per computing node.
    protected_links
        BPP / TA-BPP protected edges (undirected).
    traffic
        Optional origin-destination traffic demand matrix.
    num_trials
        Number of single-link failure events to draw.
    seed
        Random seed for reproducibility.
    failure_sampling
        'probability_weighted' or 'uniform'.
    enforce_capacity
        If True and edge capacities exist, traffic exceeding link capacity
        is dropped proportionally due to buffer exhaustion.
    drop_model
        'bottleneck' (min surviving ratio) or 'multiplicative' (product across hops).
    """
    if failure_sampling not in {"uniform", "probability_weighted"}:
        raise ValueError(
            "failure_sampling must be 'uniform' or 'probability_weighted'"
        )
    rng = random.Random(seed)
    edges = list(graph.edges())
    if not edges:
        return SimulationOutcome()

    paths = build_primary_paths(graph, next_hops_per_c)
    protected = _protected_set(protected_links)

    has_capacities = any(
        "capacity" in graph[u][v] and graph[u][v]["capacity"] is not None
        for u, v in edges
    )
    should_enforce_capacity = enforce_capacity and has_capacities

    total_traffic = sum(traffic.values()) if traffic else 0.0

    total_attempts = 0
    successful_deliveries = 0
    traffic_delivered = 0.0
    recovery_count = 0
    bpp_recovery = 0
    mnp_recovery = 0
    capacity_drop_count = 0
    peak_mlu = 0.0

    edge_weights = [
        max(0.0, float(graph[u][v].get("prob_fail", 0.0)))
        for u, v in edges
    ]
    if failure_sampling == "probability_weighted" and sum(edge_weights) > 0:
        cumulative = []
        running = 0.0
        for weight in edge_weights:
            running += weight
            cumulative.append(running)

        def draw_edge():
            draw = rng.random() * cumulative[-1]
            for index, boundary in enumerate(cumulative):
                if draw <= boundary:
                    return edges[index]
            return edges[-1]
    else:
        def draw_edge():
            return edges[rng.randrange(len(edges))]

    for _ in range(num_trials):
        failed = draw_edge()
        failed_norm = normalize_edge(*failed)
        repair_graph = graph.copy()
        if repair_graph.has_edge(*failed):
            repair_graph.remove_edge(*failed)
        repair_spt: Dict[int, Tuple[Dict, Dict]] = {}

        # First pass: determine routing paths and accumulate post-failure loads
        resolved_flows: List[Tuple[Tuple[int, int], str, float, List[Tuple[int, int]]]] = []
        post_link_loads: Dict[Tuple[int, int], float] = {}

        for (s, d), path in paths.items():
            total_attempts += 1
            tm_val = traffic.get((s, d), 0.0) if traffic else 1.0

            idx = detect_failure_point(path, failed)
            if idx == -1:
                # Path unaffected: uses normal primary path
                path_edges = [
                    normalize_edge(path[i], path[i + 1])
                    for i in range(len(path) - 1)
                ]
                for pe in path_edges:
                    post_link_loads[pe] = post_link_loads.get(pe, 0.0) + tm_val
                resolved_flows.append(((s, d), "direct", tm_val, path_edges))
                continue

            detecting = path[idx]
            hops = next_hops_per_c.get(detecting, {}).get(d, set())
            valid_alts = sorted([h for h in hops if normalize_edge(detecting, h) != failed_norm])

            recovered = False
            rec_edges: List[Tuple[int, int]] = []

            # Stage 1: Try MNP-e / LFC alternate next-hop forwarding
            if valid_alts:
                alt = valid_alts[0]
                curr = alt
                visited = set(path[:idx + 1]) | {curr}
                alt_nodes = [path[idx], curr]
                ttl = 64
                while ttl > 0:
                    if curr == d:
                        recovered = True
                        break
                    p_curr = paths.get((curr, d), [])
                    if len(p_curr) < 2:
                        break
                    next_hop = p_curr[1]
                    step_edge = normalize_edge(curr, next_hop)
                    if step_edge == failed_norm:
                        # Downstream router attempts to use the failed link
                        break
                    if next_hop in visited:
                        # Forwarding loop detected!
                        break
                    visited.add(next_hop)
                    alt_nodes.append(next_hop)
                    curr = next_hop
                    ttl -= 1

                if recovered:
                    prefix_edges = [
                        normalize_edge(path[i], path[i + 1])
                        for i in range(idx)
                    ]
                    detour_edges = [
                        normalize_edge(alt_nodes[i], alt_nodes[i + 1])
                        for i in range(len(alt_nodes) - 1)
                    ]
                    rec_edges = prefix_edges + detour_edges
                    for pe in rec_edges:
                        post_link_loads[pe] = post_link_loads.get(pe, 0.0) + tm_val
                    resolved_flows.append(((s, d), "mnp", tm_val, rec_edges))
                    recovery_count += 1
                    mnp_recovery += 1
                    continue

            # Stage 2: Fall back to BPP / TA-BPP multi-hop backup path if link is protected
            if failed_norm in protected:
                if detecting not in repair_spt:
                    repair_spt[detecting] = dijkstra(repair_graph, detecting)
                distances, predecessors = repair_spt[detecting]
                if distances.get(d, float("inf")) != float("inf"):
                    repair_path = reconstruct_path(predecessors, detecting, d)
                else:
                    repair_path = []
                if repair_path:
                    prefix_edges = [
                        normalize_edge(path[i], path[i + 1])
                        for i in range(idx)
                    ]
                    tunnel_edges = [
                        normalize_edge(repair_path[i], repair_path[i + 1])
                        for i in range(len(repair_path) - 1)
                    ]
                    rec_edges = prefix_edges + tunnel_edges
                    for pe in rec_edges:
                        post_link_loads[pe] = post_link_loads.get(pe, 0.0) + tm_val
                    resolved_flows.append(((s, d), "bpp", tm_val, rec_edges))
                    recovery_count += 1
                    bpp_recovery += 1
                    continue

            # Unrecoverable failure
            resolved_flows.append(((s, d), "lost", tm_val, []))

        # Second pass: monitor detour link loads and enforce capacity bounds
        trial_max_mlu = 0.0
        edge_surv_ratio: Dict[Tuple[int, int], float] = {}

        if should_enforce_capacity:
            for pe, load in post_link_loads.items():
                u, v = pe
                cap = graph[u][v].get("capacity") if graph.has_edge(u, v) else None
                if cap is not None and cap > 0:
                    util = load / cap
                    if util > trial_max_mlu:
                        trial_max_mlu = util
                    if load > cap:
                        edge_surv_ratio[pe] = max(0.0, cap / load)
                    else:
                        edge_surv_ratio[pe] = 1.0
                else:
                    edge_surv_ratio[pe] = 1.0

        if trial_max_mlu > peak_mlu:
            peak_mlu = trial_max_mlu

        for (s, d), status, tm_val, path_edges in resolved_flows:
            if status == "lost":
                continue

            delivery_factor = 1.0
            if should_enforce_capacity and path_edges:
                for pe in path_edges:
                    ratio = edge_surv_ratio.get(pe, 1.0)
                    if drop_model == "multiplicative":
                        delivery_factor *= ratio
                    else:
                        delivery_factor = min(delivery_factor, ratio)

            if delivery_factor < 1.0:
                capacity_drop_count += 1

            # Topological delivery requires reaching destination without complete disconnection
            if delivery_factor > 0.0:
                successful_deliveries += 1

            traffic_delivered += tm_val * delivery_factor

    avail = successful_deliveries / total_attempts if total_attempts > 0 else 1.0
    if total_traffic > 0:
        t_avail = traffic_delivered / (total_traffic * num_trials)
    else:
        t_avail = avail

    return SimulationOutcome(
        topological_availability=avail,
        traffic_availability=t_avail,
        packet_loss_proxy=1.0 - avail,
        recovery_count=recovery_count,
        bpp_recovery_count=bpp_recovery,
        mnp_recovery_count=mnp_recovery,
        capacity_drop_count=capacity_drop_count,
        max_link_utilization=peak_mlu,
        num_trials=num_trials,
    )
