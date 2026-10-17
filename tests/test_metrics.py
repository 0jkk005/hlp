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
