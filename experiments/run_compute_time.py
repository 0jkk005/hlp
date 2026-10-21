"""Compute-time experiment, reproducing the spirit of paper Figs. 8-10, 13-15.

We measure the wall-clock time per computing node for LFC (naive) vs.
MNP-e (our implementation) on synthetic topologies of varying size and
average degree. We also record the number of BPP-protected links needed
to reach availability R for HLP (paper Fig. 16).

Output: results/compute_time.csv
        results/bpp_vs_availability.csv
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Dict, List

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.append(ROOT)

from src.topology import NetworkTopology
from src.lfc import compute_lfc
from src.mnp_e import compute_mnp_e
from src.bpp import bpp
from src.utils import ensure_dir, get_logger

log = get_logger("ctime")


def _measure_compute_time(graph, fn, repeat=3) -> float:
    """Return the *per-node* average compute time, in microseconds."""
    t0 = time.perf_counter()
    for _ in range(repeat):
        for c in graph.nodes():
            fn(graph, c)
    t1 = time.perf_counter()
    per_node_s = (t1 - t0) / (repeat * graph.number_of_nodes())
    return per_node_s * 1e6  # microseconds


def run_compute_time(sizes: List[int], degrees: List[int], seed: int, out_dir: str) -> pd.DataFrame:
    ensure_dir(out_dir)
    rows: List[Dict] = []
    for n in sizes:
        for m in degrees:
            topo = NetworkTopology.generate_random(n=n, m=max(1, m // 2), seed=seed,
                                                    name=f"BA_{n}_{m}")
            G = topo.graph
            avg_deg = 2 * G.number_of_edges() / max(1, G.number_of_nodes())
            t_lfc = _measure_compute_time(G, compute_lfc)
            t_mnpe = _measure_compute_time(G, compute_mnp_e)
            rows.append(dict(
                n=n, target_degree=m, actual_degree=avg_deg,
                lfc_us_per_node=t_lfc,
                mnp_e_us_per_node=t_mnpe,
                ratio=t_lfc / t_mnpe if t_mnpe > 0 else float("nan"),
            ))
            log.info("n=%d deg=%d LFC=%.2f us MNP-e=%.2f us ratio=%.2fx",
                     n, m, t_lfc, t_mnpe, t_lfc / t_mnpe if t_mnpe > 0 else 0.0)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(out_dir, "compute_time.csv"), index=False)
    log.info("Saved -> %s", os.path.join(out_dir, "compute_time.csv"))
    return df


def run_bpp_vs_availability(topologies: List[str], R_values: List[float],
                             seed: int, out_dir: str,
                             allow_synthetic: bool = False) -> pd.DataFrame:
    """Number of BPP links needed to meet availability threshold R per topology."""
    ensure_dir(out_dir)
    rows: List[Dict] = []
    for topo_name in topologies:
        path = os.path.join(ROOT, "data", "gml", topo_name)
        if os.path.exists(path):
            topo = NetworkTopology.from_gml(path)
        else:
            if not allow_synthetic:
                raise FileNotFoundError(f"Named GML {path} missing; pass --allow-synthetic to label BA output")
            topo = NetworkTopology.generate_random(n=50, m=3, seed=seed,
                                                    name="synthetic_" + topo_name.replace(".gml", ""))
        G = topo.graph
        nh = {c: compute_mnp_e(G, c) for c in G.nodes()}
        for R in R_values:
            protected = bpp(G, nh, R=R)
            rows.append(dict(
                topology=topo.name, R=R,
                backup_links=len(protected),
                backup_ratio=len(protected) / max(1, G.number_of_edges()),
            ))
            log.info("Topo=%s R=%.4f -> BPP=%d (%.2f%% of links)",
                     topo.name, R, len(protected),
                     100 * len(protected) / max(1, G.number_of_edges()))
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(out_dir, "bpp_vs_availability.csv"), index=False)
    log.info("Saved -> %s", os.path.join(out_dir, "bpp_vs_availability.csv"))
    return df


def cli() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sizes", type=int, nargs="+", default=[20, 50, 100, 200])
    ap.add_argument("--degrees", type=int, nargs="+", default=[3, 5, 8, 10])
    ap.add_argument("--topologies", nargs="+",
                    default=["Abilene.gml", "Sprint.gml", "Geant2012.gml"])
    ap.add_argument("--R_values", type=float, nargs="+",
                    default=[0.94, 0.95, 0.96, 0.97, 0.98, 0.99, 1.0])
    ap.add_argument("--allow-synthetic", action="store_true",
                    help="Explicitly permit labeled synthetic substitutes for missing GMLs")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=str, default=os.path.join(ROOT, "results"))
    args = ap.parse_args()
    run_compute_time(args.sizes, args.degrees, args.seed, args.out)
    run_bpp_vs_availability(args.topologies, args.R_values, args.seed, args.out,
                            allow_synthetic=args.allow_synthetic)


if __name__ == "__main__":
    cli()
