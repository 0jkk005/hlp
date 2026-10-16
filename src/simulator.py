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
from .shortest_path import shortest_path
from .utils import normalize_edge


@dataclass
class SimulationOutcome:
    topological_availability: float = 0.0
    traffic_availability: float = 0.0
    packet_loss_proxy: float = 0.0
    recovery_count: int = 0
    bpp_recovery_count: int = 0
    mnp_recovery_count: int = 0
    num_trials: int = 0

    def as_dict(self) -> Dict:
        return {
            "topological_availability": self.topological_availability,
            "traffic_availability": self.traffic_availability,
            "packet_loss_proxy": self.packet_loss_proxy,
            "recovery_count": self.recovery_count,
            "bpp_recovery_count": self.bpp_recovery_count,
            "mnp_recovery_count": self.mnp_recovery_count,
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
) -> SimulationOutcome:
    """Run the Monte-Carlo single-link-failure experiment.

    Parameters
    ----------
    graph
    next_hops_per_c
        MNP-e / LFC next-hop sets per computing node.
    protected_links
        BPP / TA-BPP protected edges (undirected).
    traffic
        Optional gravity-model traffic matrix.
    num_trials
        Number of single-link failure events to draw.
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

    total_traffic = sum(traffic.values()) if traffic else 0.0

    total_attempts = 0
    successful_deliveries = 0
    traffic_delivered = 0.0
    recovery_count = 0
    bpp_recovery = 0
    mnp_recovery = 0

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

        for (s, d), path in paths.items():
            total_attempts += 1
            tm_val = traffic.get((s, d), 0.0) if traffic else 1.0

            idx = detect_failure_point(path, failed)
            if idx == -1:
                # Path not affected.
                successful_deliveries += 1
                traffic_delivered += tm_val
                continue

            detecting = path[idx]
            hops = next_hops_per_c.get(detecting, {}).get(d, set())

            if len(hops) > 1:
                # MNP-e / LFC gives an alternate next-hop.
                successful_deliveries += 1
                traffic_delivered += tm_val
                recovery_count += 1
                mnp_recovery += 1
                continue

            # No alternate next-hop; fall back to BPP / TA-BPP if available.
            if failed_norm in protected:
                # A protected link is only a valid recovery if the
                # repair path exists after removing the failed link.
                # This prevents the simulator from treating the protected
                # set as an unconditional success flag.
                repair_graph = graph.copy()
                if repair_graph.has_edge(*failed):
                    repair_graph.remove_edge(*failed)
                repair_path = shortest_path(repair_graph, detecting, d)
                if not repair_path:
                    continue
                successful_deliveries += 1
                traffic_delivered += tm_val
                recovery_count += 1
                bpp_recovery += 1
                continue

            # Otherwise the traffic is lost.

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
        num_trials=num_trials,
    )
