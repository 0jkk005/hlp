"""Counterexamples to source-wide rerouting and silent benchmark substitution."""
import networkx as nx
import pytest

from src.bpp import compute_delta_e
from src.path_construction import local_repair_path
from src.shortest_path import shortest_path
from src.ta_bpp import compute_delta_T
from src.rocketfuel import load_rocketfuel
from experiments.run_budget_sweep import run_sweep


def test_local_repair_retains_prefix_and_scoring_matches():
    # s=0 -> 1 -> 2 -> 3 is the primary route. Once (1,2) fails,
    # s can cheaply start over via 4, but router 1 must first go back to 0.
    g = nx.Graph()
    for u, v, cost in [(0, 1, 1), (1, 2, 1), (2, 3, 1),
                       (0, 4, 2), (4, 3, 2)]:
        g.add_edge(u, v, cost=cost, prob_fail=0.1)
    primary = [0, 1, 2, 3]
    failed = g.copy()
    failed.remove_edge(1, 2)
    local = local_repair_path(failed, primary)
    assert shortest_path(failed, 0, 3) == [0, 4, 3]
    assert local == [0, 1, 0, 4, 3]
    paths = {(0, 3): primary}
    # Current analytical availability is a *proxy*. Here it includes the
    # preserved prefix (0,1), unlike an end-to-end reroute. A physical
    # link reused on the return leg is counted only once for reliability.
    expected = 0.1 * 0.9 ** 3
    assert compute_delta_e(g, (1, 2), {(0, 3)}, paths) == pytest.approx(expected)
    assert compute_delta_T(g, (1, 2), {(0, 3)}, paths, {(0, 3): 10}) == pytest.approx(10 * expected)


def test_missing_named_inputs_fail_closed(tmp_path):
    with pytest.raises(FileNotFoundError, match="Rocketfuel"):
        load_rocketfuel("Exodus", data_dir=str(tmp_path))
    with pytest.raises(FileNotFoundError, match="Named topology"):
        run_sweep(["nonexistent.gml"], [2], 1, 42, str(tmp_path))
    synthetic = load_rocketfuel("Exodus", data_dir=str(tmp_path), allow_synthetic=True)
    assert synthetic.number_of_nodes() > 0
