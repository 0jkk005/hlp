"""Original BPP -- Algorithm 3 in the paper.

For every node ``v`` and destination ``d``, link ``(v, B_v(d))`` is a
*key link* if MNP-e/LFC could not find any backup next-hop, i.e.
``|N_v(d)| == 1``. Key links are aggregated, their marginal
contribution ``Δ(e)`` (Eq. 6) is computed, and they are greedily
protected in descending order until the network-availability
requirement ``A(G) >= R`` is met.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

import networkx as nx

from .availability import network_availability, path_availability
from .path_construction import build_primary_paths
from .shortest_path import dijkstra, shortest_path_in_graph_minus_edge
from .utils import normalize_edge


# --------------------------------------------------------------------------- #
# Forwarding-path index: edge -> set of (s,d) using it directionally.
# --------------------------------------------------------------------------- #


def build_edge_to_sd_index(
    paths: Dict[Tuple[int, int], List]
) -> Dict[Tuple[int, int], Set[Tuple[int, int]]]:
    """Return ``{directed edge (u,v): set of (s,d) pairs whose primary path uses (u,v)}``.

    The same (s,d) can appear under multiple directed edges (one per hop).
    Building this once is far cheaper (O(|V|^2 * avg_path_len)) than
    iterating over all paths inside key-link detection.
    """
    idx: Dict[Tuple[int, int], Set[Tuple[int, int]]] = {}
    for (s, d), path in paths.items():
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            idx.setdefault((u, v), set()).add((s, d))
    return idx


def find_key_links(
    graph: nx.Graph,
    next_hops_per_c: Dict[int, Dict[int, Set]],
    edge_index: Optional[Dict[Tuple[int, int], Set[Tuple[int, int]]]] = None,
) -> Dict[Tuple[int, int], Set[Tuple[int, int]]]:
    """Return ``{undirected e: set of (s,d) pairs using e as a *directed* key link}``.

    Implements Algorithm 3 lines 1-7. A directed key link occurs at
    node ``v`` toward ``B_v(d)``, when ``|N_v(d)| == 1``. The
    undirected link is what we register as "to protect".

    ``edge_index`` is the output of ``build_edge_to_sd_index``. We
    accept it as an optional input to avoid rebuilding inside BPP and
    TA-BPP for the same graph.
    """
    if edge_index is None:
        paths = build_primary_paths(graph, next_hops_per_c)
        edge_index = build_edge_to_sd_index(paths)

    key_links: Dict[Tuple[int, int], Set[Tuple[int, int]]] = {}
    for v in graph.nodes():
        for d, hops in next_hops_per_c.get(v, {}).items():
            if d == v:
                continue
            if len(hops) == 1:
                hop = next(iter(hops))
                e = normalize_edge(v, hop)
                sd_pairs = edge_index.get((v, hop), set())
                key_links.setdefault(e, set()).update(sd_pairs)
    return key_links


# --------------------------------------------------------------------------- #
# Δ(e) -- topological per Algorithm 3 (Eq. 6)
# --------------------------------------------------------------------------- #


def compute_delta_e(
    graph: nx.Graph,
    e: Tuple[int, int],
    sd_pairs: Set[Tuple[int, int]],
    paths: Dict[Tuple[int, int], List],
    path_avail_cache: Optional[Dict[Tuple[int, int], float]] = None,
) -> float:
    """Eq. (6): ``Δ(e) = Σ_{(s,d)∈e.P} [A*(s,d) - A(s,d)]``.

    Approximation: ``A(s,d)`` and ``A*(s,d)`` are the availabilities of
    the (single) primary shortest path and the new shortest path in
    ``G \\ e``. Same approach the existing scaffold uses.

    Optimisation: group (s,d) pairs by source ``s`` so we only run one
    Dijkstra per source per key link (instead of one per (s,d) pair).
    """
    # Group pairs by source for batched Dijkstra.
    by_source: Dict = {}
    for (s, d) in sd_pairs:
        by_source.setdefault(s, []).append(d)

    # Remove the key edge from a copy of the graph once.
    H = graph.copy()
    a, b = normalize_edge(*e)
    if H.has_edge(a, b):
        H.remove_edge(a, b)
    # Pre-run Dijkstra from every source that needs it on H.
    dij_cache: Dict = {}
    for s in by_source:
        dij_cache[s], pred_s = dijkstra(H, s)
        # We also need path reconstruction; do it here.
        dij_cache[s] = (dij_cache[s], pred_s)

    delta = 0.0
    for s, targets in by_source.items():
        dist_s, pred_s = dij_cache[s]
        for d in targets:
            orig_path = paths.get((s, d), [])
            if not orig_path:
                continue
            a_orig = path_availability(graph, orig_path) if path_avail_cache is None else path_avail_cache.get((s, d), 0.0)
            # Reconstruct the new shortest path from pred_s.
            if dist_s[d] == float("inf"):
                continue
            new_path = _walk_pred(s, d, pred_s)
            if not new_path:
                continue
            a_new = path_availability(H, new_path)
            gain = max(0.0, a_new - a_orig)
            delta += gain
    return delta


def _walk_pred(source, target, predecessors: Dict) -> List:
    cur, path = target, []
    while cur != source:
        path.append(cur)
        cur = predecessors[cur]
        if cur is None:
            return []
    path.append(source)
    path.reverse()
    return path


def bpp(
    graph: nx.Graph,
    next_hops_per_c: Dict[int, Dict[int, Set]],
    R: float = 0.999,
    max_links: Optional[int] = None,
    verbose: bool = False,
) -> List[Tuple[int, int]]:
    """Algorithm 3 in the paper.

    Parameters
    ----------
    graph : nx.Graph
    next_hops_per_c : dict
        Output of MNP-e (or LFC) for every computing node.
    R : float
        Network-availability requirement. We stop when ``A(G) >= R``.
    max_links : int or None
        Optional hard cap on the number of backup links (used by the
        TA-HLP experiments to enforce a budget). If given, the loop
        stops once ``len(protected) >= max_links`` even if R is not met.

    Returns
    -------
    protected_links : list of undirected edges (sorted by Δ descending)
    """
    paths = build_primary_paths(graph, next_hops_per_c)
    edge_index = build_edge_to_sd_index(paths)
    # Cache the original-path availability once for everyone.
    path_avail_cache: Dict[Tuple[int, int], float] = {
        (s, d): path_availability(graph, path) for (s, d), path in paths.items()
    }
    key_links = find_key_links(graph, next_hops_per_c, edge_index=edge_index)

    if verbose:
        print(f"[BPP] {len(key_links)} key links detected")

    deltas: Dict[Tuple[int, int], float] = {}
    for e, sd_pairs in key_links.items():
        deltas[e] = compute_delta_e(graph, e, sd_pairs, paths, path_avail_cache=path_avail_cache)

    sorted_keys = sorted(deltas, key=lambda x: deltas[x], reverse=True)
    V = graph.number_of_nodes()
    norm = V * (V - 1) if V > 1 else 1
    current_A = network_availability(graph, paths)

    protected: List[Tuple[int, int]] = []
    for e in sorted_keys:
        if max_links is not None and len(protected) >= max_links:
            break
        if max_links is None and current_A >= R:
            break
        protected.append(e)
        current_A += deltas[e] / norm  # Eq. update in Algorithm 3 line 19

    if verbose:
        print(f"[BPP] Protected {len(protected)} links; A(G) ~ {current_A:.4f}")
    return protected
