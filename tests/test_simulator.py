import os
import sys
import networkx as nx
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.lfc import compute_lfc
from src.simulator import simulate_failures


def test_simulator_basic_run():
    # 5-node ring graph
    G = nx.cycle_graph(5)
    for u, v in G.edges():
        G[u][v]["cost"] = 1.0
        G[u][v]["prob_fail"] = 0.01

    next_hops = {c: compute_lfc(G, c) for c in G.nodes()}
    outcome = simulate_failures(G, next_hops, [], num_trials=50, seed=42)

    # In a simple ring, single-link failures have LFC alternates for some pairs
    assert 0.0 <= outcome.topological_availability <= 1.0
    assert outcome.num_trials == 50
    assert outcome.recovery_count >= 0


def test_simulator_loop_protection():
    # Construct a line graph 0 - 1 - 2
    # If link (0, 1) fails, node 0 has no alternate and traffic is dropped
    G = nx.Graph()
    G.add_edge(0, 1, cost=1.0, prob_fail=0.01)
    G.add_edge(1, 2, cost=1.0, prob_fail=0.01)

    # Inject an intentional bad alternate next-hop that causes a loop:
    # Say node 0 has next hop {1} and an artificial bad next-hop {1}
    next_hops = {c: compute_lfc(G, c) for c in G.nodes()}

    outcome = simulate_failures(G, next_hops, [], num_trials=20, seed=42)
    assert outcome.topological_availability < 1.0  # Line graph cannot survive link cut without tunnels


def test_simulator_capacity_enforcement():
    # Triangle graph: 0-1 (cost 1), 1-2 (cost 1), 0-2 (cost 10, capacity 50)
    G = nx.Graph()
    G.add_edge(0, 1, cost=1.0, prob_fail=0.01, capacity=1000.0)
    G.add_edge(1, 2, cost=1.0, prob_fail=0.01, capacity=1000.0)
    G.add_edge(0, 2, cost=10.0, prob_fail=0.01, capacity=50.0)

    # When (0, 1) fails, flow from 0 to 1 can use detour 0-2-1
    # If traffic is 200, detour load on (0, 2) exceeds capacity 50
    next_hops = {c: compute_lfc(G, c) for c in G.nodes()}
    traffic = {(0, 1): 200.0}

    # With capacity enforcement: drops occur, delivery is penalized
    out_cap = simulate_failures(
        G, next_hops, protected_links=[(0, 1)], traffic=traffic,
        num_trials=30, seed=42, enforce_capacity=True
    )
    # With capacity enforcement disabled: no drops
    out_nocap = simulate_failures(
        G, next_hops, protected_links=[(0, 1)], traffic=traffic,
        num_trials=30, seed=42, enforce_capacity=False
    )

    assert out_cap.max_link_utilization > 1.0
    assert out_cap.capacity_drop_count > 0
    assert out_cap.traffic_availability < out_nocap.traffic_availability

