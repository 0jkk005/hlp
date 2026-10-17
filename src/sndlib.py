"""SNDlib topology and empirical NetFlow demand matrix loader."""
from __future__ import annotations

import json
import os
import random
from typing import Dict, Optional, Tuple

import networkx as nx
import numpy as np

from .topology import NetworkTopology
from .utils import get_logger

log = get_logger("sndlib")

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "sndlib"))


def load_sndlib(
    name: str,
    data_dir: Optional[str] = None,
    seed: int = 42,
) -> Tuple[nx.Graph, Dict[Tuple[int, int], float]]:
    """Load an authentic SNDlib network and its empirical NetFlow OD demand matrix.

    Returns
    -------
    graph : nx.Graph
        Undirected graph with consecutive integer nodes and edge attributes:
        'cost', 'capacity', 'prob_fail'.
    traffic_matrix : Dict[Tuple[int, int], float]
        Origin-Destination traffic demand mapping (s, d) -> flow volume.
    """
    data_dir = data_dir or DATA_DIR
    json_path = os.path.join(data_dir, f"{name.lower()}.json")
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"SNDlib dataset not found: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Build Graph
    G = nx.Graph()
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)

    for edge in data.get("edges", []):
        u = int(edge["source"])
        v = int(edge["target"])
        if u != v:
            # Use distance or default metric as integer cost
            cost = float(max(1.0, round(edge.get("dist", rng.randint(1, 10)) / 100.0)))
            capacity = float(edge.get("capacity", rng.randint(1000, 10000)))
            prob_fail = float(np_rng.uniform(0.001, 0.02))
            G.add_edge(u, v, cost=cost, capacity=capacity, prob_fail=prob_fail)

    # Re-label to consecutive integers 0..n-1
    mapping = {old: new for new, old in enumerate(sorted(G.nodes()))}
    G = nx.relabel_nodes(G, mapping)

    # 2. Extract Empirical NetFlow Demands
    raw_demands = data.get("graph", {}).get("demands", {})
    traffic_matrix: Dict[Tuple[int, int], float] = {}

    for src_str, targets in raw_demands.items():
        src_old = int(src_str)
        if src_old not in mapping:
            continue
        s = mapping[src_old]
        for dst_str, demand_val in targets.items():
            dst_old = int(dst_str)
            if dst_old not in mapping or src_old == dst_old:
                continue
            d = mapping[dst_old]
            traffic_matrix[(s, d)] = float(demand_val)

    # 3. Calibrate link capacities to baseline shortest-path load with 1.5x engineering headroom
    # This reflects realistic carrier capacity provisioning (keeping baseline utilization ~67%).
    from .shortest_path import dijkstra
    edge_loads: Dict[Tuple[int, int], float] = {tuple(sorted((u, v))): 0.0 for u, v in G.edges()}
    for s in G.nodes():
        dist_s, pred_s = dijkstra(G, s)
        for d in G.nodes():
            if s == d or (s, d) not in traffic_matrix:
                continue
            vol = traffic_matrix[(s, d)]
            curr = d
            while curr != s and curr in pred_s:
                p = pred_s[curr]
                if p is None:
                    break
                e = tuple(sorted((p, curr)))
                if e in edge_loads:
                    edge_loads[e] += vol
                curr = p

    for (u, v), load in edge_loads.items():
        G[u][v]["capacity"] = max(1000.0, float(round(load * 1.5, 0)))

    log.info(
        "Loaded SNDlib '%s': |V|=%d, |E|=%d, demands=%d, total_traffic=%.1f",
        name,
        G.number_of_nodes(),
        G.number_of_edges(),
        len(traffic_matrix),
        sum(traffic_matrix.values()),
    )
    return G, traffic_matrix
