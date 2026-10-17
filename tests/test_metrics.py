import os
import sys
import networkx as nx
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.metrics import average_path_stretch
from src.path_construction import build_all_spt_paths


def test_path_stretch_exact_shortest():
    G = nx.cycle_graph(6)
    for u, v in G.edges():
        G[u][v]["cost"] = 1.0

    paths = build_all_spt_paths(G)
    stretch = average_path_stretch(G, paths)
    
    # Pure SPT paths must have stretch == 1.0 (no extra penalty)
    assert pytest.approx(stretch, rel=1e-5) == 1.0


def test_msd_distribution_cycle():
    from src.metrics import compute_msd_distribution
    G = nx.cycle_graph(5)
    for u, v in G.edges():
        G[u][v]["cost"] = 1.0

    # In a 5-cycle, detour for edge (0, 1) is 0-4-3-2-1 (4 hops)
    res = compute_msd_distribution(G, [(0, 1)])
    assert res["mean_msd"] == 4.0
    assert res["max_msd"] == 4.0
    assert res["pct_le_3"] == 0.0
    assert res["pct_le_5"] == 100.0


def test_tcam_footprint_scaling():
    from src.metrics import compute_tcam_footprint
    G = nx.complete_graph(5) # 10 edges
    res = compute_tcam_footprint(G, num_protected_links=2)
    assert res["not_via_entries"] == 20.0
    assert res["ti_lfa_entries"] == 10.0
    assert res["c_ta_hlp_entries"] == 2.0
    assert res["reduction_pct_vs_not_via"] == 90.0
    assert res["reduction_pct_vs_ti_lfa"] == 80.0


def test_sndlib_headroom_calibration():
    from src.sndlib import load_sndlib
    G1, _ = load_sndlib("abilene", headroom_factor=1.2)
    G2, _ = load_sndlib("abilene", headroom_factor=2.0)
    for u, v in G1.edges():
        assert G2[u][v]["capacity"] >= G1[u][v]["capacity"]

