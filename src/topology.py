"""Network topology: load GML files or generate synthetic graphs.

Each edge carries:
    cost        -- integer OSPF-style metric (default 1..10)
    prob_fail   -- per-link failure probability, uniform in [0.001, 0.02]
                   (matches the paper's evaluation setup)
    capacity    -- arbitrary integer, available for capacity-aware
                   extensions (e.g., TA-HLP with a real traffic matrix)
"""
from __future__ import annotations

import os
import random
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

import networkx as nx
import numpy as np

from .utils import get_logger

log = get_logger(__name__)


@dataclass
class NetworkTopology:
    """A small wrapper around an undirected graph + helpers."""

    graph: nx.Graph
    name: str = "unnamed"
    traffic_matrix: Dict[Tuple[int, int], float] = field(default_factory=dict)

    # ------------------------------------------------------------------ load

    @classmethod
    def from_gml(
        cls,
        filepath: str,
        name: Optional[str] = None,
        seed: int = 42,
    ) -> "NetworkTopology":
        """Load an Internet Topology Zoo GML file.

        Falls back to ``random.randint`` if a numeric ``LinkMetric`` is missing.
        Re-labels nodes to consecutive integers starting from 0.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(filepath)

        # label='id' handles 'label' and 'id' variations used by ITZ GML files.
        try:
            G = nx.read_gml(filepath, label="id")
        except Exception:
            G = nx.read_gml(filepath)

        if not nx.is_connected(G):
            # Keep the largest connected component, like the paper does.
            largest = max(nx.connected_components(G), key=len)
            G = G.subgraph(largest).copy()
            log.warning("Topology not connected; keeping largest CC (%d nodes)", G.number_of_nodes())

        # Re-label to integers 0..n-1 to simplify downstream indexing.
        G = nx.convert_node_labels_to_integers(G)

        # Derive all generated edge attributes from a local, deterministic
        # RNG.  The previous implementation mixed module-global ``random``
        # and NumPy state, which made a loaded topology change between runs.
        rng = random.Random(seed)
        np_rng = np.random.default_rng(seed)
        for u, v in G.edges():
            cost = G[u][v].get("LinkMetric", rng.randint(1, 10))
            cost = _safe_number(cost, default=rng.randint(1, 10))
            G[u][v]["cost"] = float(cost)
            G[u][v]["prob_fail"] = float(np_rng.uniform(0.001, 0.02))
            G[u][v]["capacity"] = float(rng.randint(100, 1000))

        name = name or os.path.splitext(os.path.basename(filepath))[0]
        log.info("Loaded topology '%s': %d nodes, %d edges", name, G.number_of_nodes(), G.number_of_edges())
        return cls(graph=G, name=name)

    # -------------------------------------------------------------- generate

    @classmethod
    def generate_random(
        cls,
        n: int = 50,
        m: int = 2,
        seed: int = 42,
        name: str = "synthetic_ba",
    ) -> "NetworkTopology":
        """Barabási–Albert graph with random weights.

        BA is used as a generic Internet-like generator when no GML is
        available. The paper uses BRITE Waxman; BA is a comparable model.
        """
        random.seed(seed)
        np.random.seed(seed)
        G = nx.barabasi_albert_graph(n, m, seed=seed)
        for u, v in G.edges():
            G[u][v]["cost"] = float(random.randint(1, 10))
            G[u][v]["prob_fail"] = float(np.random.uniform(0.001, 0.02))
            G[u][v]["capacity"] = float(random.randint(100, 1000))
        log.info("Generated synthetic topology '%s': %d nodes, %d edges", name, n, G.number_of_edges())
        return cls(graph=G, name=name)

    # ------------------------------------------------------------ properties

    @property
    def nodes(self):
        return self.graph.nodes

    @property
    def edges(self):
        return self.graph.edges

    def summary(self) -> str:
        G = self.graph
        return (
            f"Topology '{self.name}': |V|={G.number_of_nodes()}, "
            f"|E|={G.number_of_edges()}, avg_degree={2*G.number_of_edges()/G.number_of_nodes():.2f}"
        )


# --------------------------------------------------------------------------- #


def _safe_number(value, default):
    """Best-effort numeric coercion."""
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (ValueError, TypeError):
        return float(default)
