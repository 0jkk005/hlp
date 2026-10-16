"""Hybrid Link Protection research prototype (HLP + TA-HLP).

Modules:
    topology            -- load/generate network topologies
    shortest_path       -- Dijkstra, path reconstruction
    lfc                 -- Loop-Free Criterion baseline (Algorithm 1 in paper)
    mnp_e               -- MNP-e (Algorithm 2 in paper)
    path_construction   -- Forwarding paths from next-hop sets
    traffic_matrix      -- Gravity-model traffic matrix
    availability        -- End-to-end and network availability metrics
    bpp                 -- Backup Path Protection (Algorithm 3 in paper)
    ta_bpp              -- Traffic-Aware BPP  *** new contribution ***
    protection          -- Compose HLP / TA-HLP
    simulator           -- Monte Carlo single-link-failure simulator
    metrics             -- Overhead, CPU time, path stretch
    utils               -- Logging, helpers
"""

__all__ = [
    "topology",
    "shortest_path",
    "lfc",
    "mnp_e",
    "path_construction",
    "traffic_matrix",
    "availability",
    "bpp",
    "ta_bpp",
    "protection",
    "simulator",
    "metrics",
    "utils",
]
