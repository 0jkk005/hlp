"""Loop-Free Criterion (LFC) baseline -- paper Section IV.A.

Paper Algorithm 1 is MNP, not LFC.

The naive implementation: one Dijkstra per neighbour of ``c`` (this is
what makes LFC expensive -- O(deg(c) * |E| lg |V|)). Kept here as a
*baseline* for the experiments; MNP-e replaces this for production use.
"""
from __future__ import annotations

from typing import Dict, List, Set

import networkx as nx

from .shortest_path import dijkstra, get_primary_next_hops


def compute_lfc(graph: nx.Graph, c) -> Dict[List, Set]:
    """Compute the LFC next-hop set ``N_c(v)`` for every destination ``v != c``.

    Theorem 1 of the paper:
        x is a feasible LFC next-hop to v iff  C_x(v) < C_x(c) + C_c(v).
    """
    dist_c, pred_c = dijkstra(graph, c)
    next_hops: Dict[int, Set] = {v: set() for v in graph.nodes() if v != c}

    # (1) Primary next-hops from T_c.
    for v in next_hops:
        primary = get_primary_next_hops(graph, c, v, pred_c)
        next_hops[v].update(primary)

    # (2) Backup next-hops per LFC condition.
    for x in graph.neighbors(c):
        dist_x, _ = dijkstra(graph, x)
        for v in next_hops:
            if x in next_hops[v]:
                continue  # already a primary hop
            if dist_x[v] < dist_x[c] + dist_c[v]:
                next_hops[v].add(x)

    return next_hops
