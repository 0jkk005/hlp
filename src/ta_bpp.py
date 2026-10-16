"""TA-BPP -- Traffic-Aware Backup Path Protection.  *** new contribution ***

Identical skeleton to ``bpp.bpp``; the only change is that the
marginal-gain criterion used to rank key links becomes

    Δ_T(e) = Σ_{(s,d) ∈ e.P} T(s,d) * [ A*(s,d) - A(s,d) ]

and the stopping rule may use a *backup-link budget* ``B``.

This module is a drop-in replacement for ``bpp.bpp`` and is what the
``TA-HLP`` paper presents.
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


def compute_delta_T(
    graph: nx.Graph,
    e: Tuple[int, int],
    sd_pairs: Set[Tuple[int, int]],
    paths: Dict[Tuple[int, int], List],
    traffic: Dict[Tuple[int, int], float],
    path_avail_cache: Optional[Dict[Tuple[int, int], float]] = None,
) -> float:
    """Traffic-weighted marginal contribution of protecting link ``e``."""
    by_source: Dict = {}
    for (s, d) in sd_pairs:
        by_source.setdefault(s, []).append(d)

    H = graph.copy()
    a, b = normalize_edge(*e)
    if H.has_edge(a, b):
        H.remove_edge(a, b)
    delta = 0.0
    for s, targets in by_source.items():
        dist_s, pred_s = dijkstra(H, s)
        for d in targets:
            orig_path = paths.get((s, d), [])
            if not orig_path:
                continue
            a_orig = path_avail_cache.get((s, d), 0.0) if path_avail_cache else path_availability(graph, orig_path)
            if dist_s[d] == float("inf"):
                continue
            new_path = _walk_pred(s, d, pred_s)
            if not new_path:
                continue
            a_new = path_availability(H, new_path)
            gain = max(0.0, a_new - a_orig)
            delta += traffic.get((s, d), 1.0) * gain
    return delta


def ta_bpp(
    graph: nx.Graph,
    next_hops_per_c: Dict[int, Dict[int, Set]],
    traffic: Dict[Tuple[int, int], float],
    max_links: Optional[int] = None,
    R: Optional[float] = None,
    verbose: bool = False,
) -> List[Tuple[int, int]]:
    """TA-BPP: greedy selection of key links weighted by traffic.

    Parameters
    ----------
    graph : nx.Graph
    next_hops_per_c : dict
        Output of MNP-e (or LFC).
    traffic : dict
        ``T[(s,d)]`` from the gravity model.
    max_links : int or None
        Backup-link budget ``B``. Hard cap on protected links.
    R : float or None
        Optional topological-availability requirement ``A(G) >= R``.
        Stops early if both ``R`` and ``max_links`` would be met.
    """
    paths = build_primary_paths(graph, next_hops_per_c)
    edge_index = build_edge_to_sd_index(paths)
    # Cache the original-path availability once for everyone.
    path_avail_cache: Dict[Tuple[int, int], float] = {
        (s, d): path_availability(graph, path) for (s, d), path in paths.items()
    }
    key_links = find_key_links(graph, next_hops_per_c, edge_index=edge_index)

    if verbose:
        print(f"[TA-BPP] {len(key_links)} key links detected")

    deltas: Dict[Tuple[int, int], float] = {}
    for e, sd_pairs in key_links.items():
        deltas[e] = compute_delta_T(graph, e, sd_pairs, paths, traffic,
                                    path_avail_cache=path_avail_cache)

    sorted_keys = sorted(deltas, key=lambda x: deltas[x], reverse=True)

    protected: List[Tuple[int, int]] = []
    for e in sorted_keys:
        if max_links is not None and len(protected) >= max_links:
            break
        if R is not None and _approx_A_meets(graph, protected, e, paths, R, deltas, key_links):
            break
        protected.append(e)

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
