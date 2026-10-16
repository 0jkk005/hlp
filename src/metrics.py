"""Misc metrics: overhead, path stretch, expected recovery breakdown."""
from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

import networkx as nx

from .availability import path_availability
from .path_construction import build_primary_paths
from .shortest_path import dijkstra


def backup_overhead_ratio(graph: nx.Graph, protected: Sequence[Tuple[int, int]]) -> float:
    """Fraction of network links that need BPP-tunnel protection.

    Smaller is better; matches the "backup-links" y-axis in Figs. 16-18
    of the base paper.
    """
    if graph.number_of_edges() == 0:
        return 0.0
    return len(protected) / graph.number_of_edges()


def average_path_stretch(graph: nx.Graph, paths: Dict[Tuple[int, int], List]) -> float:
    """Average stretch of the used path vs. the pure-SPT shortest path.

    Stretch = len(used path) / len(SPT shortest path). A value of 1.0
    means no extra hop penalty; the protection mechanism has not bent
    traffic away from the shortest path.
    """
    spt_lens: Dict[Tuple[int, int], int] = {}
    for s in graph.nodes():
        dist_s, _ = dijkstra(graph, s)
        for d in graph.nodes():
            if s != d:
                spt_lens[(s, d)] = dist_s[d]

    total_stretch = 0.0
    count = 0
    for (s, d), path in paths.items():
        sp_len = spt_lens.get((s, d), 1)
        if sp_len > 0:
            total_stretch += len(path) - 1
            total_stretch /= sp_len
            count += 1
    return total_stretch / count if count > 0 else 1.0


def expected_protected_fraction(
    graph: nx.Graph,
    next_hops_per_c: Dict[int, Dict[int, set]],
    protected: Sequence[Tuple[int, int]],
) -> float:
    """Fraction of (s,d) pairs that have either an MNP alternate or a BPP tunnel.

    A pair (s,d) is "covered" if -- along the primary path from s to d --
    no link is unprotected, i.e. for every link on the path either:
      * the detecting node has |next-hops| > 1, OR
      * the link itself is in the protected set.
    """
    paths = build_primary_paths(graph, next_hops_per_c)
    protected_set = {(min(u, v), max(u, v)) for u, v in protected}
    covered = 0
    for (s, d), path in paths.items():
        ok = True
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            edge = (min(u, v), max(u, v))
            hops = next_hops_per_c.get(u, {}).get(d, set())
            if len(hops) == 1 and edge not in protected_set:
                ok = False
                break
        if ok:
            covered += 1
    return covered / len(paths) if paths else 1.0


def average_path_availability(graph: nx.Graph, paths: Dict[Tuple[int, int], List]) -> float:
    """Mean end-to-end single-path availability across (s,d) pairs."""
    if not paths:
        return 1.0
    return sum(path_availability(graph, p) for p in paths.values()) / len(paths)
