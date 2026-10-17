"""Dijkstra SPT and path reconstruction utilities.

The paper assumes an SPT rooted at every node (OSPF behaviour). We
implement Dijkstra with a binary heap; complexity O(|E| lg |V|).
"""
from __future__ import annotations

import heapq
from typing import Dict, List, Optional, Tuple

import networkx as nx

from .utils import normalize_edge


def dijkstra(graph: nx.Graph, source, weight: str = "cost") -> Tuple[Dict, Dict]:
    """Compute SPT ``T_source`` from ``source``.

    Returns
    -------
    distances : dict
        ``distances[v]`` = shortest cost from ``source`` to ``v``.
    predecessors : dict
        ``predecessors[v]`` = *first* predecessor on a shortest path
        from ``source`` to ``v``. (The paper's primary-next-hop is
        well-defined as long as we break ties deterministically.)
    """
    distances = {n: float("inf") for n in graph.nodes()}
    distances[source] = 0.0
    predecessors: Dict = {n: None for n in graph.nodes()}

    pq: List[Tuple[float, int, object]] = [(0.0, 0, source)]  # (dist, tie-break, node)
    counter = 1
    while pq:
        d, _, u = heapq.heappop(pq)
        if d > distances[u]:
            continue
        for v, data in graph[u].items():
            w = data.get(weight, 1.0)
            nd = d + w
            if nd < distances[v]:
                distances[v] = nd
                predecessors[v] = u
                heapq.heappush(pq, (nd, counter, v))
                counter += 1
    return distances, predecessors


def reconstruct_path(predecessors: Dict, source, target) -> List:
    """Reconstruct vertex sequence from a predecessor map."""
    if source == target:
        return [source]
    path = [target]
    cur = target
    while cur != source:
        cur = predecessors.get(cur)
        if cur is None:
            return []
        path.append(cur)
    path.reverse()
    return path


def shortest_path(graph: nx.Graph, source, target, weight: str = "cost") -> List:
    """Return the vertex sequence of a shortest path from ``source`` to ``target``."""
    if source == target:
        return [source]
    distances, predecessors = dijkstra(graph, source, weight=weight)
    if distances.get(target, float("inf")) == float("inf"):
        return []
    return reconstruct_path(predecessors, source, target)


def shortest_path_in_graph_minus_edge(
    graph: nx.Graph, source, target, blocked
) -> List:
    """Shortest path between ``source`` and ``target`` avoiding one undirected edge.

    ``blocked`` is an unordered pair. The edge is removed in a *copy*
    to avoid mutating the caller's graph.
    """
    H = graph.copy()
    a, b = normalize_edge(*blocked)
    if H.has_edge(a, b):
        H.remove_edge(a, b)
    return shortest_path(H, source, target)


def get_primary_next_hops(graph: nx.Graph, source, target, predecessors: Dict) -> List:
    """Return *all* immediate next-hops from ``source`` toward ``target``.

    With deterministic tie-breaking on our Dijkstra this is exactly one
    value, but we still iterate for clarity and to match the paper's
    "next-hop set" semantics.
    """
    if source == target:
        return []
    next_hops = set()
    cur = target
    while cur is not None and cur != source:
        prev = predecessors[cur]
        if prev is None:
            return []
        if prev == source:
            next_hops.add(cur)
            break
        cur = prev
    return list(next_hops)
