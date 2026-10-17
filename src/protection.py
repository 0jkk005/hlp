"""Compose MNP-e with BPP (HLP) and MNP-e with TA-BPP (TA-HLP)."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import networkx as nx

from .bpp import bpp
from .lfc import compute_lfc
from .mnp_e import compute_mnp_e
from .ta_bpp import ta_bpp


@dataclass
class ProtectionResult:
    """Holds everything a scheme produces about a topology."""

    method: str
    next_hops: Dict[int, Dict[int, Set]] = field(default_factory=dict)
    protected_links: List[Tuple[int, int]] = field(default_factory=list)
    compute_time_s: float = 0.0
    extra: Dict = field(default_factory=dict)


def compute_lfc_scheme(graph: nx.Graph) -> ProtectionResult:
    """Just LFC -- no BPP tunnel protection. Baseline for our experiments."""
    t0 = time.perf_counter()
    next_hops = {c: compute_lfc(graph, c) for c in graph.nodes()}
    t1 = time.perf_counter()
    return ProtectionResult(
        method="LFC",
        next_hops=next_hops,
        protected_links=[],
        compute_time_s=t1 - t0,
    )


def compute_hlp(
    graph: nx.Graph,
    R: float = 0.999,
    max_links: Optional[int] = None,
) -> ProtectionResult:
    """HLP = MNP-e + BPP. Stage 1 computes MNP-e for every node; stage 2 picks BPP links."""
    t0 = time.perf_counter()
    next_hops = {c: compute_mnp_e(graph, c) for c in graph.nodes()}
    protected = bpp(graph, next_hops, R=R, max_links=max_links, verbose=False)
    t1 = time.perf_counter()
    return ProtectionResult(
        method="HLP",
        next_hops=next_hops,
        protected_links=protected,
        compute_time_s=t1 - t0,
    )


def compute_ta_hlp(
    graph: nx.Graph,
    traffic: Dict[Tuple[int, int], float],
    R: Optional[float] = None,
    max_links: Optional[int] = None,
    capacity_constrained: bool = True,
) -> ProtectionResult:
    """C-TA-HLP = MNP-e + C-TA-BPP (Capacity-Constrained Traffic-Adaptive)."""
    t0 = time.perf_counter()
    next_hops = {c: compute_mnp_e(graph, c) for c in graph.nodes()}
    protected = ta_bpp(
        graph,
        next_hops,
        traffic,
        max_links=max_links,
        R=R,
        capacity_constrained=capacity_constrained,
        verbose=False,
    )
    t1 = time.perf_counter()
    return ProtectionResult(
        method="TA-HLP",
        next_hops=next_hops,
        protected_links=protected,
        compute_time_s=t1 - t0,
        extra={"traffic_total": sum(traffic.values())},
    )
