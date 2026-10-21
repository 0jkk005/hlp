"""BPP-inspired topological greedy selection, NOT a faithful Algorithm 3.

The base paper associates a key edge (v, B_v(d)) with detector-origin
pair (v, d), then evaluates Eq. 6 by path-set availability. This code
instead indexes ALL upstream (s,d) pairs traversing the edge and scores
the local detour using a single-route reliability proxy. This deliberate
extension cannot reproduce the base paper's availability threshold or
published compute times; see docs/BASE_PAPER_COMPARISON.md.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

import networkx as nx

from .availability import network_availability, path_availability
from .path_construction import build_primary_paths, detect_failure_point
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

    Extends Algorithm 3 lines 1-7 to *all upstream flows*. A directed key link occurs at
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
# Δ(e) -- single-route proxy; NOT the paper Algorithm 3 Eq. 6
# --------------------------------------------------------------------------- #


def compute_delta_e(
    graph: nx.Graph,
    e: Tuple[int, int],
    sd_pairs: Set[Tuple[int, int]],
    paths: Dict[Tuple[int, int], List],
    path_avail_cache: Optional[Dict[Tuple[int, int], float]] = None,
) -> float:
    """Heuristic gain for a local repair when edge ``e`` fails.

    A flow keeps its prefix through the upstream failure detector and
    tunnels from there to its destination. The gain proxy multiplies the
    failed-edge probability by a reliability proxy for the route. This is
    not an exact conditional-failure marginal or a faithful derivation of
    the base paper's Eq. (6); see docs/CORRECTIONS_CHECKLIST.md.
    """
    H = graph.copy()
    a, b = normalize_edge(*e)
    H.remove_edge(a, b)
    p_fail_e = float(graph[a][b].get("prob_fail", 0.01))
    # Cache one SPT per detecting router, not per origin. At an intermediate
    # failure, the packet keeps its already-forwarded prefix.
    detector_spts: Dict = {}
    delta = 0.0
    for s, d in sd_pairs:
        primary = paths.get((s, d), [])
        if not primary:
            continue
        idx = detect_failure_point(primary, e)
        if idx < 0:
            continue
        detector = primary[idx]
        if detector not in detector_spts:
            detector_spts[detector] = dijkstra(H, detector)
        distances, predecessors = detector_spts[detector]
        if distances[d] == float("inf"):
            continue
        detour = _walk_pred(detector, d, predecessors)
        if detour:
            # Reliability proxy; this is NOT an exact conditional single-
            # failure probability (see docs/CORRECTIONS_CHECKLIST.md).
            delta += p_fail_e * path_availability(H, primary[:idx] + detour)
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
    """Greedy topology-only BPP-inspired comparator (not exact Algorithm 3).

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
        current_A += deltas[e] / norm  # additive proxy, not certified paper A(G)

    if verbose:
        print(f"[BPP] Protected {len(protected)} links; A(G) ~ {current_A:.4f}")
    return protected
