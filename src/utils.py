"""Logging and small helpers shared across the codebase."""
from __future__ import annotations

import logging
import os
import random
import sys
from typing import Iterable, List, Sequence, Tuple

import networkx as nx
import numpy as np


def get_logger(name: str = "hlp", level: int = logging.INFO) -> logging.Logger:
    """Return a configured logger that writes to stderr."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(level)
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def set_seed(seed: int = 42) -> None:
    """Seed Python, NumPy, and NetworkX random sources."""
    random.seed(seed)
    np.random.seed(seed)
    # NetworkX uses Python's random by default in our generator paths.


def ensure_dir(path: str) -> str:
    """Create ``path`` if it does not exist; return the absolute path."""
    abs_path = os.path.abspath(path)
    os.makedirs(abs_path, exist_ok=True)
    return abs_path


def normalize_edge(u, v) -> Tuple[int, int]:
    """Canonical (min, max) representation for an undirected edge."""
    a, b = (u, v) if u <= v else (v, u)
    return (a, b)


def edges_undirected(path: Sequence) -> List[Tuple[int, int]]:
    """Return both orientations of every consecutive edge in a path."""
    edges = []
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        edges.append((u, v))
        edges.append((v, u))
    return edges


def node_label_iter(graph: nx.Graph) -> Iterable:
    """Standardized iterator over nodes."""
    return graph.nodes()
