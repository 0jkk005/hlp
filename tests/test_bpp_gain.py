import os
import sys
import networkx as nx
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.lfc import compute_lfc
from src.bpp import bpp, find_key_links
from src.ta_bpp import ta_bpp


def test_bpp_positive_deltas():
    # Construct a cycle with a key bridge
    # 0 - 1 - 2
    # |       |
    # 3 - 4 - 5
    # with bridge (2, 6) -> 6 has only 2 as neighbor
    G = nx.Graph()
    G.add_edge(0, 1, cost=1.0, prob_fail=0.01)
    G.add_edge(1, 2, cost=1.0, prob_fail=0.01)
    G.add_edge(0, 3, cost=1.0, prob_fail=0.01)
    G.add_edge(3, 4, cost=1.0, prob_fail=0.01)
    G.add_edge(4, 5, cost=1.0, prob_fail=0.01)
    G.add_edge(2, 5, cost=1.0, prob_fail=0.01)
    G.add_edge(2, 6, cost=1.0, prob_fail=0.02)
    G.add_edge(5, 6, cost=2.0, prob_fail=0.02)

    next_hops = {c: compute_lfc(G, c) for c in G.nodes()}
    key_links = find_key_links(G, next_hops)
    assert len(key_links) > 0

    protected = bpp(G, next_hops, max_links=2)
    assert len(protected) <= 2
    assert len(protected) > 0


def test_ta_bpp_ranking_skew():
    # On a symmetric topology where two links compete for protection,
    # TA-BPP must prioritize the link carrying heavier traffic demand.
    G = nx.Graph()
    # 0 - 1 - 3
    # |       |
    # 0 - 2 - 3
    G.add_edge(0, 1, cost=1.0, prob_fail=0.01)
    G.add_edge(1, 3, cost=1.0, prob_fail=0.01)
    G.add_edge(0, 2, cost=1.0, prob_fail=0.01)
    G.add_edge(2, 3, cost=1.0, prob_fail=0.01)

    next_hops = {c: compute_lfc(G, c) for c in G.nodes()}

    # Assign heavy traffic to flow (0, 1) and negligible traffic to flow (0, 2)
    traffic = {
        (0, 1): 1000.0,
        (1, 0): 1000.0,
        (0, 2): 1.0,
        (2, 0): 1.0,
        (1, 3): 500.0,
        (3, 1): 500.0,
        (2, 3): 1.0,
        (3, 2): 1.0,
        (0, 3): 100.0,
        (3, 0): 100.0,
    }

    protected_ta = ta_bpp(G, next_hops, traffic=traffic, max_links=1)
    assert len(protected_ta) == 1
    # Key link carrying heavy traffic must be selected first
    # Link (0, 1) carries 1000x the traffic of (0, 2)
    assert protected_ta[0] in [(0, 1), (1, 3)]


def test_c_ta_bpp_capacity_penalty():
    # If a detour link is heavily constrained by capacity,
    # the congestion penalty Phi(e) must down-rank that detour.
    G = nx.Graph()
    # 0 - 1 - 3
    # |       |
    # 0 - 2 - 3
    # If link (0, 1) fails, flow (0, 1) detours via 0 -> 2 -> 3 -> 1.
    # If link (0, 2) has a severe capacity bottleneck (e.g., 5 Mbps),
    # while traffic demand is 1000 Mbps, Phi((0, 1)) must penalize the gain by 5/1000.
    G.add_edge(0, 1, cost=1.0, capacity=10000.0, prob_fail=0.01)
    G.add_edge(1, 3, cost=1.0, capacity=10000.0, prob_fail=0.01)
    G.add_edge(0, 2, cost=1.0, capacity=10.0, prob_fail=0.01)    # Severe bottleneck!
    G.add_edge(2, 3, cost=1.0, capacity=10000.0, prob_fail=0.01)

    next_hops = {c: compute_lfc(G, c) for c in G.nodes()}
    traffic = {
        (0, 1): 1000.0,
        (1, 0): 1000.0,
        (0, 2): 10.0,
        (2, 0): 10.0,
    }

    # Without capacity constraints, (0, 1) would be chosen due to 1000 vs 10 traffic
    prot_unconstrained = ta_bpp(G, next_hops, traffic=traffic, max_links=1, capacity_constrained=False)
    assert prot_unconstrained[0] in [(0, 1), (1, 0)]

    # With capacity constraints, (0, 1)'s detour traverses bottleneck (0, 2), getting heavily penalized
    from src.ta_bpp import compute_delta_T, compute_baseline_loads
    from src.path_construction import build_primary_paths
    from src.bpp import build_edge_to_sd_index, find_key_links
    paths = build_primary_paths(G, next_hops)
    base_loads = compute_baseline_loads(G, paths, traffic)
    delta_unconstrained = compute_delta_T(G, (0, 1), {(0, 1)}, paths, traffic, capacity_constrained=False)
    delta_constrained = compute_delta_T(G, (0, 1), {(0, 1)}, paths, traffic, baseline_loads=base_loads, capacity_constrained=True)
    assert delta_constrained < delta_unconstrained
    assert delta_constrained > 0.0

