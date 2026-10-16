"""TBFH - Two Backup Fast Hop-by-hop (Merindol et al., 2011).

Per the base paper (Geng et al. 2020, Table 1):
    "TBFH achieves faster computation by tightening DC, but still needs
     to construct multiple SPTs.  Time complexity: 2 * O(|E| lg |V|)
     per computing node."

TBFH enforces the Downstream Criterion (DC) -- a *stronger*
requirement than LFC:

    x is a valid backup next-hop from c to v (TBFH) iff
        C_x(v) < C_c(v)
    (x is strictly closer to v than c is).

For "two SPTs per node" we compute:
    1. The SPT from c (the primary one).
    2. The SPT from x*, where x* is the neighbour of c with the
       smallest C_x(c). (i.e. the cheapest peer.)

TBFH's coverage is *strictly lower* than LFC's because DC is a
stronger criterion -- this matches the paper's measurements in
Table 4 (TBFH column always below LFC/MNP-e).

Reference: P. Merindol, P. Francois, O. Bonaventure, S. Cateloin,
   and J. J. Pansiot, "An efficient algorithm to enable path diversity
   in link state routing networks," Comput. Netw. 55(5), 2011.
"""
from __future__ import annotations

from typing import Dict, Set

import networkx as nx

from .shortest_path import dijkstra, get_primary_next_hops


def compute_tbfh(graph: nx.Graph, c) -> Dict[int, Set]:
    """Compute TBFH backup next-hops for node ``c``.

    Two SPTs are constructed per node: T_c and T_{x*}, where x* is the
    cheapest-cost neighbour of c. Backup next-hops are suggested by
    the Downstream Criterion (DC).
    """
    dist_c, pred_c = dijkstra(graph, c)
    next_hops: Dict[int, Set] = {v: set() for v in graph.nodes() if v != c}

    # 1. Primary next-hops from T_c (identical to LFC/MNP-e).
    for v in next_hops:
        next_hops[v].update(get_primary_next_hops(graph, c, v, pred_c))

    # 2. Pick x* = neighbour of c with the lowest cost -- but if c has
    #    only one neighbour, we still build one extra SPT (x = that
    #    neighbour), giving exactly 2 SPTs.
    x_star = None
    best_cost = float("inf")
    for x in graph.neighbors(c):
        # cost to reach x from c is just L(c, x)
        cost_x = graph[c][x].get("cost", 1.0)
        if cost_x < best_cost:
            best_cost = cost_x
            x_star = x

    if x_star is None:
        # c is isolated; no backup possible.
        return next_hops

    # 3. Build the SPT from x* (the "second" SPT of TBFH).
    dist_x, _ = dijkstra(graph, x_star)

    # 4. Suggest x* as a backup next-hop for every v where DC holds:
    #    C_{x*}(v) < C_c(v).
    for v in next_hops:
        if x_star in next_hops[v]:
            continue
        if dist_x[v] < dist_c[v]:
            next_hops[v].add(x_star)

    # 5. (TBFH also offers load balancing by exploring a second-best x*;
    #    we omit it for brevity. The paper's comparison table evaluates
    #    TBFH with the basic 2-SPT variant.)
    return next_hops
