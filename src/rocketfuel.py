"""Rocketfuel ISP topology loader.

Rocketfuel maps (Spring et al., SIGCOMM 2002 / IMC 2004) are not GML.
The canonical format used by the public CAIDA release has lines of the
form:

    # comment
    <nodeId> <name> <latitude> <longitude> ...
    <linkId> <u> <v> <weight> ...

We support two formats:

1. Rocketfuel ``.cch`` style -- nodes and links intermixed.
   To use it, drop a file like ``data/rocketfuel/Exodus.cch``.
2. Simple edge-list format -- one ``u v weight`` per line.
   Drop a file like ``data/rocketfuel/Exodus.edgelist``.

If no file is found we fall back to a reproducible synthetic
Barabasi-Albert graph whose node and edge counts match the values
reported in Geng et al. 2020 (Table 3):

    Exodus   : 79  nodes, 147 edges
    Telstra  : 108 nodes, 153 edges
    Tiscali  : 161 nodes, 328 edges
    Sprint   : 315 nodes, 972 edges

This fallback is explicitly logged as such -- it reproduces the *scale*
of the topology (so compute-time experiments are still representative)
but not its exact structure. For an exact reproduction, download the
Rocketfuel dataset from
https://www.caida.org/projects/ark/rocketfuel/ and drop the files into
``data/rocketfuel/``.
"""
from __future__ import annotations

import os
import random
from typing import Optional, Tuple

import networkx as nx
import numpy as np

from .utils import get_logger

log = get_logger("rocketfuel")


# Paper-reported counts (Geng et al., 2020, Table 3).
# Used only for synthetic fallback.
PAPER_COUNTS = {
    "Exodus":   (79,  147),
    "Telstra":  (108, 153),
    "Tiscali":  (161, 328),
    "Sprint315": (315, 972),  # distinct from the Topology Zoo "Sprint" (11 nodes)
}


def _parse_cch(path: str) -> nx.Graph:
    """Parse an authentic University of Washington / CAIDA ``.cch`` Rocketfuel file.

    Format per README.cch:
        uid @loc [+] [bb] (num_neigh) [&ext] -> <nuid-1> <nuid-2> ... {-euid} ... =name[!] rn
    Internal intra-AS router neighbors are enclosed in angle brackets ``<...>``.
    """
    import re
    G = nx.Graph()
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#") or "->" not in line:
                continue
            parts = line.split("->")
            left = parts[0].strip().split()
            if not left:
                continue
            try:
                u = int(left[0])
            except ValueError:
                continue
            if u < 0:
                continue
            right = parts[1].split("=")[0]
            nbrs = re.findall(r"<(\d+)>", right)
            for nbr_str in nbrs:
                v = int(nbr_str)
                if u != v:
                    G.add_edge(u, v, cost=1.0)
    return G


def _parse_edgelist(path: str) -> nx.Graph:
    """Parse a simple ``u v [w]`` edge list."""
    G = nx.Graph()
    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            try:
                u, v = int(parts[0]), int(parts[1])
                w = float(parts[2]) if len(parts) >= 3 else 1.0
            except ValueError:
                continue
            if u != v:
                G.add_edge(u, v, cost=w)
    return G


def _synthetic_match(name: str, n: int, m_edges: int, seed: int = 42) -> nx.Graph:
    """A reproducible BA-like graph whose |V|,|E| match the paper."""
    rng = random.Random(seed)
    # Choose BA m-parameter so final edge count is close to target.
    # BA(n, m_ba) has ~ (n - m_ba) * m_ba edges; solve roughly.
    m_ba = max(1, round(m_edges / max(1, n)))
    G = nx.barabasi_albert_graph(n=n, m=m_ba, seed=seed)

    # Adjust edge count by randomly adding/removing edges.
    nodes = list(G.nodes())
    while G.number_of_edges() < m_edges:
        u = rng.choice(nodes)
        v = rng.choice(nodes)
        if u != v and not G.has_edge(u, v):
            G.add_edge(u, v)
    while G.number_of_edges() > m_edges:
        edges = list(G.edges())
        e = edges[rng.randrange(len(edges))]
        G.remove_edge(*e)

    # Strip to largest connected component so we have one network.
    largest = max(nx.connected_components(G), key=len)
    G = G.subgraph(largest).copy()
    G = nx.convert_node_labels_to_integers(G)
    return G


def load_rocketfuel(
    name: str,
    data_dir: Optional[str] = None,
    seed: int = 42,
) -> nx.Graph:
    """Load (or synthesise) a Rocketfuel topology by canonical name.

    Looks for ``<data_dir>/<name>.cch`` first, then ``<name>.edgelist``.
    Falls back to a synthetic BA graph matching the paper's counts and
    emits a warning so downstream consumers know the structure is not
    the inferred one.
    """
    data_dir = data_dir or os.path.join(
        os.path.dirname(__file__), "..", "data", "rocketfuel"
    )
    data_dir = os.path.abspath(data_dir)

    # Try to load the real file.
    for ext, fn in (("cch", _parse_cch), ("edgelist", _parse_edgelist)):
        path = os.path.join(data_dir, f"{name}.{ext}")
        if os.path.exists(path):
            log.info("Loaded Rocketfuel '%s' from %s", name, path)
            G = fn(path)
            if G.number_of_nodes() == 0:
                break
            if not nx.is_connected(G):
                largest = max(nx.connected_components(G), key=len)
                G = G.subgraph(largest).copy()
            G = nx.convert_node_labels_to_integers(G)
            _annotate(G, seed=seed)
            return G

    # Fallback: synthetic graph matching the paper's (|V|, |E|).
    if name not in PAPER_COUNTS:
        raise ValueError(f"Unknown Rocketfuel topology '{name}'. "
                           f"Known: {list(PAPER_COUNTS)}")
    n, m_edges = PAPER_COUNTS[name]
    log.warning("Rocketfuel data file for '%s' not found in %s; "
                "falling back to synthetic BA graph matching the paper's "
                "(|V|=%d, |E|=%d). The structure is NOT the inferred ISP map.",
                name, data_dir, n, m_edges)
    G = _synthetic_match(name, n, m_edges, seed=seed)
    _annotate(G, seed=seed)
    return G


def _annotate(G: nx.Graph, seed: int = 42) -> None:
    """Add simulation-required edge attributes (cost, prob_fail, capacity)."""
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)
    for u, v in G.edges():
        if "cost" not in G[u][v]:
            G[u][v]["cost"] = float(rng.randint(1, 10))
        G[u][v]["prob_fail"] = float(np_rng.uniform(0.001, 0.02))
        G[u][v]["capacity"] = float(rng.randint(100, 1000))

