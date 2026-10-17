import os
import sys
import networkx as nx
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.shortest_path import dijkstra, shortest_path, shortest_path_in_graph_minus_edge, get_primary_next_hops


def test_dijkstra_triangle():
    G = nx.Graph()
    G.add_edge(0, 1, cost=1.0)
    G.add_edge(1, 2, cost=2.0)
    G.add_edge(0, 2, cost=10.0)

    dist, pred = dijkstra(G, 0)
    assert dist[0] == 0.0
    assert dist[1] == 1.0
    assert dist[2] == 3.0  # via 1
    assert pred[2] == 1
    assert pred[1] == 0

    path = shortest_path(G, 0, 2)
    assert path == [0, 1, 2]


def test_shortest_path_in_graph_minus_edge():
    G = nx.Graph()
    G.add_edge(0, 1, cost=1.0)
    G.add_edge(1, 2, cost=1.0)
    G.add_edge(0, 2, cost=5.0)

    # When (0, 1) is blocked, shortest path from 0 to 2 must use (0, 2)
    path = shortest_path_in_graph_minus_edge(G, 0, 2, (0, 1))
    assert path == [0, 2]


def test_get_primary_next_hops():
    G = nx.Graph()
    G.add_edge(0, 1, cost=1.0)
    G.add_edge(1, 2, cost=1.0)
    dist, pred = dijkstra(G, 0)
    nh = get_primary_next_hops(G, 0, 2, pred)
    assert nh == [1]
