"""Network-availability metrics.

Topological availability (paper definition, Eq. (3)):
    A(s,d) computed via Inclusion-Exclusion over all paths (intractable
    in general -- we provide both an exact variant for tiny graphs and
    a single-path approximation used everywhere in the experiments).
    A(G)  = mean of A(s,d) over (s,d).

Traffic-weighted availability (TA-HLP contribution):
    T_A(G) = sum_{s!=d} T(s,d) * A(s,d)  /  sum T(s,d)
"""
from __future__ import annotations

from itertools import combinations
from typing import Dict, List, Optional, Sequence, Tuple

import networkx as nx

from .shortest_path import shortest_path
from .utils import normalize_edge


# ---------------------------------------------------------------- single-path


def path_availability(graph: nx.Graph, path: Sequence) -> float:
    """Availability of one path (product of per-link reliabilities)."""
    if len(path) < 2:
        return 1.0
    p = 1.0
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        p *= (1.0 - graph[u][v].get("prob_fail", 0.0))
    return p


def network_availability(graph: nx.Graph, paths: Dict[Tuple[int, int], List]) -> float:
    """Single-path approximation of A(G) (Eq. 3)."""
    n = graph.number_of_nodes()
    if n <= 1:
        return 1.0
    total = sum(path_availability(graph, p) for p in paths.values())
    return total / (n * (n - 1))


def traffic_availability(
    graph: nx.Graph,
    paths: Dict[Tuple[int, int], List],
    traffic: Dict[Tuple[int, int], float],
) -> float:
    """Single-path approximation of T_A(G)."""
    if not traffic:
        return network_availability(graph, paths)
    num = 0.0
    den = 0.0
    for (s, d), path in paths.items():
        w = traffic.get((s, d), 0.0)
        if w <= 0:
            continue
        num += w * path_availability(graph, path)
        den += w
    return num / den if den > 0 else 0.0


# ----------------------------------------------------------- path enumeration


def _enumerate_paths(graph: nx.Graph, source, target, cutoff: int = 6) -> List[List]:
    """Enumerate simple paths of length <= ``cutoff`` between ``source`` and ``target``."""
    paths: List[List] = []

    def dfs(node, path):
        if node == target:
            paths.append(list(path))
            return
        if len(path) >= cutoff:
            return
        for nbr in graph.neighbors(node):
            if nbr in path:
                continue
            path.append(nbr)
            dfs(nbr, path)
            path.pop()

    dfs(source, [source])
    return paths


def exact_end_to_end_availability(graph: nx.Graph, source, target, cutoff: int = 5) -> float:
    """Eq. (2) in the paper: Inclusion-Exclusion over enumerated simple paths.

    Exponential in path count; intended only for very small graphs (sanity checks).
    """
    if source == target:
        return 1.0
    paths = _enumerate_paths(graph, source, target, cutoff=cutoff)
    if not paths:
        return 0.0
    n = len(paths)

    def avail(p):
        a = 1.0
        for i in range(len(p) - 1):
            u, v = p[i], p[i + 1]
            a *= (1.0 - graph[u][v].get("prob_fail", 0.0))
        return a

    # Pre-compute per-path availabilities and the union-link-set for each subset.
    avail_vec = [avail(p) for p in paths]
    total = 0.0
    for k in range(1, n + 1):
        for combo in combinations(range(n), k):
            # P(A_i1 ∧ ... ∧ A_ik) = product of per-link reliabilities over the union.
            union_links = set()
            for idx in combo:
                p = paths[idx]
                for i in range(len(p) - 1):
                    union_links.add(normalize_edge(p[i], p[i + 1]))
            pa = 1.0
            for (u, v) in union_links:
                pa *= (1.0 - graph[u][v].get("prob_fail", 0.0))
            sign = 1 if (k % 2 == 1) else -1
            total += sign * pa
    return max(0.0, min(1.0, total))


# --------------------------------------------------------------- availability


def link_availability(graph: nx.Graph, u, v) -> float:
    return 1.0 - graph[u][v].get("prob_fail", 0.0)
