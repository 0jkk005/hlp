"""Traffic-matrix generation.

The base paper is purely topological; it does not define a traffic
matrix. For TA-HLP we adopt a degree-based gravity model, the standard
workload approximation when no flow data is available.

    T(s,d) = (deg(s) * deg(d)) / sum_k deg(k) * scale * jitter
"""
from __future__ import annotations

import random
from typing import Dict, Optional, Tuple

import networkx as nx


def gravity_traffic_matrix(
    graph: nx.Graph,
    scale: float = 1.0,
    jitter: float = 0.1,
    seed: Optional[int] = None,
) -> Dict[Tuple[int, int], float]:
    """Return ``T`` such that ``T[(s,d)]`` is the traffic demand from ``s`` to ``d``.

    Parameters
    ----------
    graph : nx.Graph
    scale : float
        Multiplicative constant; absolute scale does not affect
        traffic-availability ratios.
    jitter : float
        Symmetric multiplicative noise (``1 ± jitter``) to break
        symmetry among similarly-connected node pairs.
    seed : int or None
        Reproducible jitter.
    """
    rng = random.Random(seed)
    total_deg = sum(dict(graph.degree()).values()) or 1
    T: Dict[Tuple[int, int], float] = {}
    deg = dict(graph.degree())
    for s in graph.nodes():
        for d in graph.nodes():
            if s == d:
                continue
            base = (deg[s] * deg[d]) / total_deg
            T[(s, d)] = base * scale * rng.uniform(1.0 - jitter, 1.0 + jitter)
    return T


def total_traffic(T: Dict[Tuple[int, int], float]) -> float:
    """Sum of all entries in the traffic matrix."""
    return sum(T.values())
