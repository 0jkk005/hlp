"""C-TA-BPP -- Capacity-Constrained Traffic-Adaptive Backup Path Protection.

Identical skeleton to ``bpp.bpp``; the marginal-gain criterion used to rank
key links incorporates both traffic demand weights and the downstream
Congestion Penalty Factor:

    Δ_{C-T}(e) = Φ(e) * Σ_{(s,d) ∈ e.P} T(s,d) * p_e * A(P_repair(e))

where Φ(e) = Π_{k ∈ P_repair(e)} min(1.0, C_k / L_post(k)) penalizes
overloaded detours, and the stopping rule enforces a backup-link budget ``B``.
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
from .path_construction import build_primary_paths, path_uses_link
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
    accumulated_detour_loads: Optional[Dict[Tuple[int, int], float]] = None,
    return_shifts: bool = False,
) -> float | Tuple[float, Dict[Tuple[int, int], float]]:
    """Traffic-weighted marginal contribution of protecting link ``e``,
    incorporating downstream capacity congestion penalty factor Phi(e).
    """
    by_source: Dict = {}
    for (s, d) in sd_pairs:
        by_source.setdefault(s, []).append(d)

    H = graph.copy()
    a, b = normalize_edge(*e)
    if H.has_edge(a, b):
        H.remove_edge(a, b)
    delta = 0.0
    detour_shifts: Dict[Tuple[int, int], float] = {}

    for s, targets in by_source.items():
        dist_s, pred_s = dijkstra(H, s)
        for d in targets:
            orig_path = paths.get((s, d), [])
            if not orig_path:
                continue
            if dist_s[d] == float("inf"):
                continue
            new_path = _walk_pred(s, d, pred_s)
            if not new_path:
                continue
            # Repair path availability in G \ {e}
            a_repair = path_availability(H, new_path)
            # Marginal traffic-weighted availability gain:
            # When key link e fails (probability p_fail_e), the backup path rescues flow (s, d).
            # The saved traffic volume is T(s, d) * p_fail_e * a_repair.
            p_fail_e = float(graph[a][b].get("prob_fail", 0.01))
            gain = p_fail_e * a_repair
            flow_vol = traffic.get((s, d), 1.0)
            delta += flow_vol * gain

            # Track detour link loads for congestion penalty
            if capacity_constrained and baseline_loads:
                for i in range(len(new_path) - 1):
                    k_edge = normalize_edge(new_path[i], new_path[i + 1])
                    detour_shifts[k_edge] = detour_shifts.get(k_edge, 0.0) + flow_vol

    # Apply continuous Congestion Penalty Factor:
    # Phi(e) = prod_{k in repair} min(1.0, C_k / L_post(k))
    if capacity_constrained and baseline_loads and detour_shifts:
        phi = 1.0
        for k_edge, shift in detour_shifts.items():
            u_k, v_k = k_edge
            if graph.has_edge(u_k, v_k):
                cap = graph[u_k][v_k].get("capacity", None)
                if cap is not None and cap > 0:
                    prior_acc = (
                        accumulated_detour_loads.get(k_edge, 0.0)
                        if accumulated_detour_loads is not None
                        else 0.0
                    )
                    post_load = baseline_loads.get(k_edge, 0.0) + prior_acc + shift
                    if post_load > cap:
                        phi *= min(1.0, cap / post_load)
        delta *= phi

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
        ``T[(s,d)]`` from empirical NetFlow or gravity model.
    max_links : int or None
        Backup-link budget ``B``. Hard cap on protected links.
    R : float or None
        Optional topological-availability requirement ``A(G) >= R``.
        Stops early if both ``R`` and ``max_links`` would be met.
    capacity_constrained : bool
        If True, applies Congestion Penalty Factor Phi(e) to prevent
        buffer exhaustion on detour paths.
    iterative : bool
        If True, executes true iterative greedy selection, re-evaluating
        marginal gains and cumulative detour congestion at each selection step.
        If False, executes static single-pass ranking.
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
        # Static single-pass ranking (baseline/ablation mode)
        for e, sd_pairs in key_links.items():
            deltas[e] = compute_delta_T(
                graph, e, sd_pairs, paths, traffic,
                path_avail_cache=path_avail_cache,
                baseline_loads=baseline_loads,
                capacity_constrained=capacity_constrained,
            )
        sorted_keys = sorted(deltas, key=lambda x: deltas[x], reverse=True)
        for e in sorted_keys:
            if max_links is not None and len(protected) >= max_links:
                break
            if R is not None and _approx_A_meets(graph, protected, e, paths, R, deltas, key_links):
                break
            protected.append(e)
    else:
        # True Iterative Greedy Selection (Nemhauser-Wolsey-Fisher conforming)
        remaining_keys = set(key_links.keys())
        accumulated_detour_loads: Dict[Tuple[int, int], float] = {
            normalize_edge(*e): 0.0 for e in graph.edges()
        }
        target_budget = max_links if max_links is not None else len(key_links)

        while remaining_keys and len(protected) < target_budget:
            best_e = None
            best_delta = -1.0
            best_shifts: Dict[Tuple[int, int], float] = {}

            for e in remaining_keys:
                delta_e, shifts_e = compute_delta_T(
                    graph, e, key_links[e], paths, traffic,
                    path_avail_cache=path_avail_cache,
                    baseline_loads=baseline_loads,
                    capacity_constrained=capacity_constrained,
                    accumulated_detour_loads=accumulated_detour_loads,
                    return_shifts=True,
                )
                if delta_e > best_delta:
                    best_delta = delta_e
                    best_e = e
                    best_shifts = shifts_e

            if best_e is None or best_delta <= 0.0:
                break

            deltas[best_e] = best_delta
            if R is not None and _approx_A_meets(graph, protected, best_e, paths, R, deltas, key_links):
                break

            protected.append(best_e)
            remaining_keys.remove(best_e)

            # Update accumulated detour load with expected failure volume
            u_b, v_b = best_e
            p_fail = float(graph[u_b][v_b].get("prob_fail", 0.01))
            for k_edge, shift_vol in best_shifts.items():
                accumulated_detour_loads[k_edge] = (
                    accumulated_detour_loads.get(k_edge, 0.0) + p_fail * shift_vol
                )

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
