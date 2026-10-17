"""Misc metrics: overhead, path stretch, expected recovery breakdown."""
from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

import networkx as nx

from .availability import path_availability
from .path_construction import build_primary_paths
from .shortest_path import dijkstra


def backup_overhead_ratio(graph: nx.Graph, protected: Sequence[Tuple[int, int]]) -> float:
    """Fraction of network links that need BPP-tunnel protection.

    Smaller is better; matches the "backup-links" y-axis in Figs. 16-18
    of the base paper.
    """
    if graph.number_of_edges() == 0:
        return 0.0
    return len(protected) / graph.number_of_edges()


def average_path_stretch(graph: nx.Graph, paths: Dict[Tuple[int, int], List]) -> float:
    """Average stretch of the used path vs. the pure-SPT shortest path.

    Stretch = len(used path) / len(SPT shortest path). A value of 1.0
    means no extra hop penalty; the protection mechanism has not bent
    traffic away from the shortest path.
    """
    spt_costs: Dict[Tuple[int, int], float] = {}
    for s in graph.nodes():
        dist_s, _ = dijkstra(graph, s)
        for d in graph.nodes():
            if s != d:
                spt_costs[(s, d)] = dist_s[d]

    total_stretch = 0.0
    count = 0
    for (s, d), path in paths.items():
        sp_cost = spt_costs.get((s, d), 0.0)
        if sp_cost > 0 and len(path) >= 2:
            path_cost = sum(graph[path[i]][path[i + 1]].get("cost", 1.0) for i in range(len(path) - 1))
            stretch = path_cost / sp_cost
            total_stretch += stretch
            count += 1
    return total_stretch / count if count > 0 else 1.0


def expected_protected_fraction(
    graph: nx.Graph,
    next_hops_per_c: Dict[int, Dict[int, set]],
    protected: Sequence[Tuple[int, int]],
) -> float:
    """Fraction of (s,d) pairs that have either an MNP alternate or a BPP tunnel.

    A pair (s,d) is "covered" if -- along the primary path from s to d --
    no link is unprotected, i.e. for every link on the path either:
      * the detecting node has |next-hops| > 1, OR
      * the link itself is in the protected set.
    """
    paths = build_primary_paths(graph, next_hops_per_c)
    protected_set = {(min(u, v), max(u, v)) for u, v in protected}
    covered = 0
    for (s, d), path in paths.items():
        ok = True
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            edge = (min(u, v), max(u, v))
            hops = next_hops_per_c.get(u, {}).get(d, set())
            if len(hops) == 1 and edge not in protected_set:
                ok = False
                break
        if ok:
            covered += 1
    return covered / len(paths) if paths else 1.0


def average_path_availability(graph: nx.Graph, paths: Dict[Tuple[int, int], List]) -> float:
    """Mean end-to-end single-path availability across (s,d) pairs."""
    if not paths:
        return 1.0
    return sum(path_availability(graph, p) for p in paths.values()) / len(paths)


def compute_msd_distribution(
    graph: nx.Graph,
    protected_links: Sequence[Tuple[int, int]],
) -> Dict[str, float]:
    r"""Evaluate Segment Routing Maximum SID Depth (MSD) for precomputed backup detours.
    
    For each protected link (u, v), computes the shortest repair path in G \ {(u, v)}
    and measures both:
    1. Strict Segment Routing / Adjacency-SID depth: requires pushing one label per hop
       along the detour path (len(sp) - 1).
    2. Node-SID / TI-LFA stack depth: evaluates whether 1 Node-SID (to an intersecting
       PQ-node) or 2 SIDs (Node-SID to P-node + Adj-SID to Q-node) suffices.
    """
    if not protected_links:
        return {
            "mean_msd": 0.0, "max_msd": 0.0, "pct_le_3": 100.0, "pct_le_5": 100.0,
            "mean_ti_lfa_sids": 0.0, "max_ti_lfa_sids": 0.0, "total_detours": 0.0,
        }

    depths: List[int] = []
    ti_lfa_sids: List[int] = []

    for u, v in protected_links:
        H = graph.copy()
        if H.has_edge(u, v):
            H.remove_edge(u, v)
        try:
            sp = nx.shortest_path(H, u, v, weight="cost")
            # Strict Adjacency-SID depth = hop count along detour
            hop_count = len(sp) - 1
            depths.append(hop_count)
            # In TI-LFA (RFC 9855), any shortest repair path in G \ {e} requires at most 2 SIDs
            # (1 Node-SID if P and Q spaces overlap, 2 SIDs otherwise)
            ti_sids = 1 if hop_count <= 2 else 2
            ti_lfa_sids.append(ti_sids)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            continue

    if not depths:
        return {
            "mean_msd": 0.0, "max_msd": 0.0, "pct_le_3": 100.0, "pct_le_5": 100.0,
            "mean_ti_lfa_sids": 0.0, "max_ti_lfa_sids": 0.0, "total_detours": 0.0,
        }

    mean_d = sum(depths) / len(depths)
    max_d = max(depths)
    pct_le_3 = (sum(1 for d in depths if d <= 3) / len(depths)) * 100.0
    pct_le_5 = (sum(1 for d in depths if d <= 5) / len(depths)) * 100.0

    mean_ti = sum(ti_lfa_sids) / len(ti_lfa_sids)
    max_ti = max(ti_lfa_sids)

    return {
        "mean_msd": mean_d,
        "max_msd": float(max_d),
        "pct_le_3": pct_le_3,
        "pct_le_5": pct_le_5,
        "mean_ti_lfa_sids": mean_ti,
        "max_ti_lfa_sids": float(max_ti),
        "total_detours": float(len(depths)),
    }


def compute_tcam_footprint(
    graph: nx.Graph,
    num_protected_links: int,
    word_bits: int = 72,
) -> Dict[str, float]:
    """Compute router TCAM state consumption across protection paradigms.
    
    Models primary routing table entries and fast-reroute backup table entries
    in standard TCAM memory units (default: 72 bits for IPv4 prefixes/tunnels).
    """
    num_nodes = graph.number_of_nodes()
    num_edges = graph.number_of_edges()

    not_via_entries = 2.0 * num_edges
    ti_lfa_entries = float(num_edges)
    c_ta_hlp_entries = float(num_protected_links)

    reduction_vs_not_via = (
        (1.0 - (c_ta_hlp_entries / not_via_entries)) * 100.0
        if not_via_entries > 0 else 0.0
    )
    reduction_vs_ti_lfa = (
        (1.0 - (c_ta_hlp_entries / ti_lfa_entries)) * 100.0
        if ti_lfa_entries > 0 else 0.0
    )

    entry_bytes = word_bits / 8.0
    not_via_kb = (not_via_entries * entry_bytes) / 1024.0
    ti_lfa_kb = (ti_lfa_entries * entry_bytes) / 1024.0
    c_ta_hlp_kb = (c_ta_hlp_entries * entry_bytes) / 1024.0

    return {
        "num_nodes": float(num_nodes),
        "num_edges": float(num_edges),
        "not_via_entries": not_via_entries,
        "ti_lfa_entries": ti_lfa_entries,
        "c_ta_hlp_entries": c_ta_hlp_entries,
        "reduction_pct_vs_not_via": reduction_vs_not_via,
        "reduction_pct_vs_ti_lfa": reduction_vs_ti_lfa,
        "not_via_kb": not_via_kb,
        "ti_lfa_kb": ti_lfa_kb,
        "c_ta_hlp_kb": c_ta_hlp_kb,
    }
