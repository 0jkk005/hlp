import os
import sys
import networkx as nx
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.lfc import compute_lfc
from src.shortest_path import dijkstra


def test_lfc_condition_validity():
    # Construct a 4-node diamond graph
    # 0 - 1 - 3
    # |       |
    # 2 ------+
    G = nx.Graph()
    G.add_edge(0, 1, cost=1.0)
    G.add_edge(0, 2, cost=1.0)
    G.add_edge(1, 3, cost=1.0)
    G.add_edge(2, 3, cost=1.0)

    # For node 0 to destination 3:
    # Primary paths could be 0-1-3 or 0-2-3 (cost 2)
    next_hops = compute_lfc(G, 0)
    
    # Destination 3 should have candidate next hops
    assert 3 in next_hops
    assert len(next_hops[3]) >= 1

    # Verify that every candidate next-hop x in next_hops[v] satisfies Theorem 1:
    # C_x(v) < C_x(c) + C_c(v)
    dist_c, _ = dijkstra(G, 0)
    for v, candidates in next_hops.items():
        for x in candidates:
            dist_x, _ = dijkstra(G, x)
            # Must satisfy loop-free condition
            assert dist_x[v] < dist_x[0] + dist_c[v]
