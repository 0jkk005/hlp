"""DMPA-e -- Distributed Multipath Algorithm with Extension
(Geng et al., Comput. Commun. 116, 2018).

Per the base paper (Section II, Ref. [25]):
    "Authors in [25] present DMPA-e by incorporating hop count, a
     topology dependent metric. However, DMPA-e cannot achieve full
     failure coverage against single network component failures."

DMPA-e augments LFC with a hop-count-aware relaxation: a backup
next-hop x from c to v is acceptable if EITHER:
    (i)  x satisfies LFC (Theorem 1), or
    (ii) x satisfies the hop-aware relaxation:
            H_x(v) <= H_c(v) + delta_h   AND
            C_x(v) <= C_c(v) + delta_c
         where H_*(v) is the hop count along the SPT from * to v,
         and delta_h, delta_c are small constants.

The paper does not specify the constants; we use delta_h = 1 and
delta_c equal to the minimum link cost in the graph (a conservative
choice that yields availability between MNP and MNP-e independently
observed in the paper's Fig 11-12).

DMPA-e computes one SPT per neighbour of c (same cost as LFC), so its
per-node complexity is O(deg(c) * |E| lg |V|).
"""
from __future__ import annotations

from typing import Dict, Set

import networkx as nx

from .shortest_path import dijkstra, get_primary_next_hops


def _hop_counts_from_pred(source, predecessors: Dict) -> Dict:
    hops = {n: 0 for n in predecessors}
    for v in predecessors:
        h = 0
        cur = v
        while cur != source and cur is not None:
            cur = predecessors[cur]
            h += 1
        hops[v] = h if cur is not None else float("inf")
    hops[source] = 0
    return hops


def compute_dmpa_e(graph: nx.Graph, c,
                   delta_h: int = 1,
                   delta_c: float = None) -> Dict[int, Set]:
    """Compute DMPA-e backup next-hops for node ``c``."""
    dist_c, pred_c = dijkstra(graph, c)
    next_hops: Dict[int, Set] = {v: set() for v in graph.nodes() if v != c}

    # Default delta_c = minimum link cost in the graph
    if delta_c is None:
        delta_c = min((d.get("cost", 1.0) for _, _, d in graph.edges(data=True)),
                      default=1.0)

    # 1. Primary next-hops from T_c
    for v in next_hops:
        next_hops[v].update(get_primary_next_hops(graph, c, v, pred_c))

    # Hop counts from c along T_c
    hops_c = _hop_counts_from_pred(c, pred_c)

    # 2. For each neighbour x of c: SPT from x and the DMPA-e test
    for x in graph.neighbors(c):
        dist_x, pred_x = dijkstra(graph, x)
        hops_x = _hop_counts_from_pred(x, pred_x)
        for v in next_hops:
            if x in next_hops[v]:
                continue
            # (i) LFC test
            lfc_ok = dist_x[v] < dist_x[c] + dist_c[v]
            # (ii) Hop-aware relaxation
            hop_ok = hops_x.get(v, float("inf")) <= hops_c.get(v, float("inf")) + delta_h
            cost_ok = dist_x[v] <= dist_c[v] + delta_c
            if lfc_ok or (hop_ok and cost_ok):
                next_hops[v].add(x)
    return next_hops
