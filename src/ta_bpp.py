"""C-TA-BPP -- Capacity-Constrained Traffic-Adaptive Backup Path Protection.

Identical skeleton to ``bpp.bpp``; the marginal-gain criterion used to rank
key links incorporates both traffic demand weights and the downstream
per-flow bottleneck delivery proxy:

    Δ(e) = Σ_{(s,d) affected by e} T(s,d) * p_e * A(P_local_repair) * q(s,d,e)

where q is a per-flow bottleneck delivery proxy. It is not an exact
capacity-feasible optimization or a steady-state availability estimator.
See docs/CORRECTIONS_CHECKLIST.md before interpreting results.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

import networkx as nx

from .availability import path_availability, network_availability
from .bpp import (
    build_edge_to_sd_index,
    find_key_links,
    _walk_pred,
)
from .path_construction import build_primary_paths, detect_failure_point
from .shortest_path import dijkstra
from .utils import normalize_edge


def compute_baseline_loads(
    graph: nx.Graph,
    paths: Dict[Tuple[int, int], List],
    traffic: Dict[Tuple[int, int], float],
) -> Dict[Tuple[int, int], float]:
    """Compute baseline shortest-path traffic load L_0(k) for all edges."""
    loads: Dict[Tuple[int, int], float] = {normalize_edge(*e): 0.0 for e in graph.edges()}
    for (s, d), path in paths.items():
        vol = traffic.get((s, d), 0.0)
        if vol <= 0.0:
            continue
        for i in range(len(path) - 1):
            e_norm = normalize_edge(path[i], path[i + 1])
            if e_norm in loads:
                loads[e_norm] += vol
    return loads


def compute_delta_T(
    graph: nx.Graph,
    e: Tuple[int, int],
    sd_pairs: Set[Tuple[int, int]],
    paths: Dict[Tuple[int, int], List],
    traffic: Dict[Tuple[int, int], float],
    path_avail_cache: Optional[Dict[Tuple[int, int], float]] = None,
    baseline_loads: Optional[Dict[Tuple[int, int], float]] = None,
    capacity_constrained: bool = False,
    accumulated_detour_loads: Optional[Dict[Tuple[int, int], float]] = None,  # deprecated; ignored
    return_shifts: bool = False,
) -> float | Tuple[float, Dict[Tuple[int, int], float]]:
    """Traffic-weighted marginal contribution of protecting link ``e``,
    with a per-flow capacity-delivery proxy for this failure scenario.
    """
    H = graph.copy()
    a, b = normalize_edge(*e)
    H.remove_edge(a, b)
    detector_spts: Dict = {}
    affected = []
    detour_shifts: Dict[Tuple[int, int], float] = {}
    # Local repair preserves the path prefix, matching BPP forwarding in
    # simulator.py. Do not treat an end-to-end reroute as a local repair.
    for s, d in sd_pairs:
        primary = paths.get((s, d), [])
        if not primary:
            continue
        idx = detect_failure_point(primary, e)
        if idx < 0:
            continue
        detector = primary[idx]
        if detector not in detector_spts:
            detector_spts[detector] = dijkstra(H, detector)
        distances, predecessors = detector_spts[detector]
        if distances[d] == float("inf"):
            continue
        detour = _walk_pred(detector, d, predecessors)
        if not detour:
            continue
        repair_path = primary[:idx] + detour
        flow_vol = traffic.get((s, d), 0.0)
        edges = [normalize_edge(repair_path[i], repair_path[i + 1])
                 for i in range(len(repair_path) - 1)]
        affected.append((flow_vol, path_availability(H, repair_path), edges))
        if capacity_constrained:
            for edge in edges:
                detour_shifts[edge] = detour_shifts.get(edge, 0.0) + flow_vol

    p_fail_e = float(graph[a][b].get("prob_fail", 0.01))
    delta = 0.0
    for flow_vol, repair_avail, edges in affected:
        delivery_factor = 1.0
        if capacity_constrained and baseline_loads is not None:
            # Per-flow bottleneck proxy for THIS failure only. This is
            # NOT a full per-scenario load model: unaffected and LFA
            # flows require separate accounting before publication.
            for edge in edges:
                u, v = edge
                cap = graph[u][v].get("capacity")
                if cap is not None and cap > 0:
                    post_load = baseline_loads.get(edge, 0.0) + detour_shifts.get(edge, 0.0)
                    delivery_factor = min(delivery_factor, min(1.0, cap / post_load)
                                          if post_load > 0 else 1.0)
        delta += flow_vol * p_fail_e * repair_avail * delivery_factor
    if return_shifts:
        return delta, detour_shifts
    return delta


def ta_bpp(
    graph: nx.Graph,
    next_hops_per_c: Dict[int, Dict[int, Set]],
    traffic: Dict[Tuple[int, int], float],
    max_links: Optional[int] = None,
    R: Optional[float] = None,
    capacity_constrained: bool = False,
    iterative: bool = True,
    verbose: bool = False,
) -> List[Tuple[int, int]]:
    """C-TA-BPP: Capacity-Constrained Traffic-Adaptive selection of key links.

    Parameters
    ----------
    graph : nx.Graph
    next_hops_per_c : dict
        Output of MNP-e (or LFC).
    traffic : dict
        ``T[(s,d)]`` from an OD demand instance or gravity model.
    max_links : int or None
        Backup-link budget ``B``. Hard cap on protected links.
    R : float or None
        Optional topological-availability requirement ``A(G) >= R``.
        Stops early if both ``R`` and ``max_links`` would be met.
    capacity_constrained : bool
        If True, applies a per-flow bottleneck delivery heuristic. It
        does not guarantee feasibility or prevent buffer exhaustion.
    iterative : bool
        Retained for API compatibility. Under mutually exclusive single-link
        failures the score of one edge does not change when another is protected.
    """
    paths = build_primary_paths(graph, next_hops_per_c)
    edge_index = build_edge_to_sd_index(paths)
    path_avail_cache: Dict[Tuple[int, int], float] = {
        (s, d): path_availability(graph, path) for (s, d), path in paths.items()
    }
    key_links = find_key_links(graph, next_hops_per_c, edge_index=edge_index)
    baseline_loads = compute_baseline_loads(graph, paths, traffic) if capacity_constrained else None

    if verbose:
        print(f"[C-TA-BPP] {len(key_links)} key links detected (iterative={iterative})")

    if not key_links:
        return []

    protected: List[Tuple[int, int]] = []
    deltas: Dict[Tuple[int, int], float] = {}

    if not iterative:
        # Single-pass ranking under exclusive single-link failures
        for e, sd_pairs in key_links.items():
            deltas[e] = compute_delta_T(
                graph, e, sd_pairs, paths, traffic,
                path_avail_cache=path_avail_cache,
                baseline_loads=baseline_loads,
                capacity_constrained=capacity_constrained,
            )
        sorted_keys = sorted(deltas, key=lambda x: (-deltas[x], x))
        for e in sorted_keys:
            if max_links is not None and len(protected) >= max_links:
                break
            if R is not None and _approx_A_meets(graph, protected, e, paths, R, deltas, key_links):
                break
            protected.append(e)
    else:
        # Under an exclusive single-edge-failure model, protecting one
        # candidate cannot add load to a DIFFERENT failure scenario. Thus
        # static and iterative rankings coincide for this proxy objective.
        remaining_keys = sorted(key_links)
        target_budget = max_links if max_links is not None else len(remaining_keys)
        while remaining_keys and len(protected) < target_budget:
            scored = [(compute_delta_T(
                graph, e, key_links[e], paths, traffic,
                path_avail_cache=path_avail_cache, baseline_loads=baseline_loads,
                capacity_constrained=capacity_constrained,
            ), e) for e in remaining_keys]
            best_delta, best_e = max(scored, key=lambda item: (item[0], tuple(-x for x in item[1])))
            if best_delta <= 0.0:
                break
            deltas[best_e] = best_delta
            if R is not None and _approx_A_meets(graph, protected, best_e, paths, R, deltas, key_links):
                break
            protected.append(best_e)
            remaining_keys.remove(best_e)

    if verbose:
        print(f"[TA-BPP] Protected {len(protected)} links")
    return protected


def _approx_A_meets(
    graph: nx.Graph,
    protected: List[Tuple[int, int]],
    candidate: Tuple[int, int],
    paths: Dict[Tuple[int, int], List],
    R: float,
    deltas: Dict[Tuple[int, int], float],
    key_links: Dict[Tuple[int, int], Set[Tuple[int, int]]],
) -> bool:
    """Would *adding* enough key links already push ``A(G)`` past ``R``?

    Conservative shortcut: only stop once we've already accumulated
    enough Δ such that ``A_base + Σ Δ / N >= R``. We don't bother to
    account for the candidate itself; this just stops the budget loop
    once ``R`` is comfortably satisfied.
    """
    n = graph.number_of_nodes()
    norm = n * (n - 1) if n > 1 else 1
    base = sum(path_availability(graph, p) for p in paths.values()) / norm
    accumulated = sum(deltas.get(e, 0.0) for e in protected) / norm
    return (base + accumulated) >= R
