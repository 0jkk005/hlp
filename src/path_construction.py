"""Forwarding-path construction from next-hop sets.

The paper assumes that, at every node ``c`` and for every destination
``d``, the router uses a *primary* next-hop (the first element of
``N_c(d)``) and falls back to other next-hops in ``N_c(d)`` if the
primary link fails. BPP-protected links are activated only when the
multi-hop repair path (a tunnel) is invoked.

This module produces the deterministic primary path that every (s,d)
pair would use *with* the protection scheme in place. It also provides
helpers for routing-while-failure simulation.
"""
from __future__ import annotations

from typing import Dict, List, Set, Tuple

import networkx as nx

from .shortest_path import dijkstra, get_primary_next_hops
from .utils import edges_undirected, normalize_edge


def build_primary_paths(graph: nx.Graph, next_hops_per_c: Dict[int, Dict[int, Set]]) -> Dict[Tuple[int, int], List]:
    """Construct the primary forwarding path used by every (s, d) pair.

    For every source ``s``, run Dijkstra to compute primary next-hops
    (using the *shortest path tree* of ``s``), then walk the resulting
    tree to produce the primary path from ``s`` to every ``d``.

    The ``next_hops_per_c`` argument is the output of MNP-e or LFC and
    is consulted only for documentation; the primary path itself is
    always the SPT path.
    """
    paths: Dict[Tuple[int, int], List] = {}
    for s in graph.nodes():
        dist_s, pred_s = dijkstra(graph, s)
        for d in graph.nodes():
            if s == d:
                continue
            path = _walk_path(s, d, pred_s)
            if path:
                paths[(s, d)] = path
    return paths


def build_all_spt_paths(graph: nx.Graph) -> Dict[Tuple[int, int], List]:
    """Convenience: same as ``build_primary_paths`` but ignores next-hops."""
    return build_primary_paths(graph, {})


def _walk_path(source, target, predecessors: Dict) -> List:
    cur, path = target, []
    while cur != source:
        path.append(cur)
        cur = predecessors.get(cur)
        if cur is None:
            return []
    path.append(source)
    path.reverse()
    return path


def detect_failure_point(path: List, failed_edge: Tuple[int, int]) -> int:
    """Return the index of the failed edge on ``path`` (-1 if not present)."""
    a, b = normalize_edge(*failed_edge)
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        if (u, v) == (a, b) or (v, u) == (a, b):
            return i
    return -1


def path_uses_link(path: List, edge: Tuple[int, int]) -> bool:
    a, b = normalize_edge(*edge)
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        if (u, v) == (a, b) or (v, u) == (a, b):
            return True
    return False


def links_on_path(path: List) -> List[Tuple[int, int]]:
    """Undirected edge list along a path."""
    return [(path[i], path[i + 1]) for i in range(len(path) - 1)]


def local_repair_path(repair_graph: nx.Graph, primary_path: List) -> List:
    """Return prefix + local repair from the upstream failure detector.

    ``repair_graph`` must already have the failed edge removed. This is the
    same BPP route shape as the failure simulator: packets cannot rewind to
    their source when an intermediate router detects a broken link. Returns
    an empty path when the failure is not on the primary path or no local
    repair exists.
    """
    for i in range(len(primary_path) - 1):
        if not repair_graph.has_edge(primary_path[i], primary_path[i + 1]):
            detector, destination = primary_path[i], primary_path[-1]
            distances, predecessors = dijkstra(repair_graph, detector)
            if distances[destination] == float("inf"):
                return []
            from .shortest_path import reconstruct_path
            detour = reconstruct_path(predecessors, detector, destination)
            return primary_path[:i] + detour if detour else []
    return []
