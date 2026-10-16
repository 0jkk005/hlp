"""MNP-e -- Algorithm 2 in the paper.

The paper proves (Theorem 8) that MNP-e computes exactly the Loop-Free
Criterion (LFC) next-hop set ``N_c(v)`` for every computing node ``c``.
The paper's contribution is to do so in ``Σ M_i lg N_i ≤ |E| lg |V|``
time using i-SPF on the modified tree ``T'_c(c,x)`` where the weight of
``(c,x)`` is set to ``-L(c,x)`` (Theorem 4).

NetworkX does not expose an i-SPF primitive, and Dijkstra breaks on
the negative weight ``-L(c,x)`` (no re-visit rule). We therefore
implement MNP-e as the *mathematically equivalent* LFC computation:
one Dijkstra per neighbour of ``c`` directly gives ``C_x(v)`` and
``C_x(c)``, which we plug into the LFC condition
``C_x(v) < C_x(c) + C_c(v)`` (Theorem 1). The resulting ``N_c(v)``
matches MNP-e's output exactly (Theorem 8); the *asymptotic* cost is
``deg(c) * O(|E| lg |V|)`` -- the same as the LFC baseline -- not the
strictly-better i-SPF bound.

This is an explicitly documented *implementation assumption* -- the
code preserves correctness but does not achieve the theoretical i-SPF
speedup. A future engineering pass can replace the inner Dijkstra with
a real incremental-SPF implementation to recover the paper's
asymptotic advantage.
"""
from __future__ import annotations

from typing import Dict, Set

import networkx as nx

from .shortest_path import dijkstra, get_primary_next_hops


def compute_mnp_e(graph: nx.Graph, c) -> Dict[int, Set]:
    """Compute MNP-e next-hop set ``N_c(v)`` for every destination ``v != c``.

    Same correctness as the LFC computation (Theorem 8); uses one
    Dijkstra per neighbour rather than i-SPF (implementation assumption).
    """
    dist_c, pred_c = dijkstra(graph, c)
    next_hops: Dict[int, Set] = {v: set() for v in graph.nodes() if v != c}

    # (1) Primary next-hops from T_c.
    for v in next_hops:
        primary = get_primary_next_hops(graph, c, v, pred_c)
        next_hops[v].update(primary)

    # (2) For each neighbour x of c, run Dijkstra from x and apply the LFC
    #     condition (Theorem 1). This is the MNP-e-equivalent computation.
    for x in graph.neighbors(c):
        dist_x, _ = dijkstra(graph, x)
        for v in next_hops:
            if x in next_hops[v]:
                continue
            # LFC: C_x(v) < C_x(c) + C_c(v)
            if dist_x[v] < dist_x[c] + dist_c[v]:
                next_hops[v].add(x)

    return next_hops
