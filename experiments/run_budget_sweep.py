"""Main experiment for the paper: sweep backup-link budget B and compare
LFC, HLP (MNP-e + BPP), and TA-HLP (MNP-e + TA-BPP) on Traffic Availability.

Output: results/budget_sweep_<topo>.csv and a combined CSV
        results/all_topologies.csv  with columns
            topology, budget, method, topological_availability,
            traffic_availability, packet_loss_proxy, backup_links,
            compute_time_s, num_trials
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Dict, List

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.append(ROOT)

from src.topology import NetworkTopology
from src.traffic_matrix import gravity_traffic_matrix
from src.protection import compute_lfc_scheme, compute_hlp, compute_ta_hlp
from src.tbfh import compute_tbfh
from src.dmpa_e import compute_dmpa_e
from src.simulator import simulate_failures
from src.utils import ensure_dir, get_logger

log = get_logger("sweep")


DEFAULT_TOPOS = ["Sprint.gml", "Abilene.gml", "Geant2012.gml"]
DEFAULT_BUDGETS = [2, 4, 6, 8, 10, 12, 14, 16]
EXPECTED_TOPOLOGY_SIZES = {
    "Abilene": (11, 14),
    "Geant2012": (22, 36),
    "Sprint": (315, 972),
}


def _resolve_topo_path(name: str) -> str:
    """Look for ``data/gml/<name>`` in the project root; return '' if missing."""
    path = os.path.join(ROOT, "data", "gml", name)
    if os.path.exists(path):
        return path
    return ""


def run_sweep(
    topologies: List[str],
    budgets: List[int],
    num_trials: int,
    seed: int,
    out_dir: str,
    include_extended_baselines: bool = False,
    replicates: int = 1,
) -> pd.DataFrame:
    if replicates < 1:
        raise ValueError("replicates must be at least 1")
    rows: List[Dict] = []
    ensure_dir(out_dir)

    for replicate in range(replicates):
        replicate_seed = seed + replicate
        for topo_name in topologies:
            gml_path = _resolve_topo_path(topo_name)
            if gml_path:
                topo = NetworkTopology.from_gml(gml_path, seed=replicate_seed)
            else:
                n = 30
                m = 3
                log.warning(
                    "Topology '%s' missing -> falling back to BA(%d,%d)",
                    topo_name, n, m,
                )
                topo = NetworkTopology.generate_random(
                    n=n, m=m, seed=replicate_seed,
                    name=topo_name.replace(".gml", ""),
                )

            G = topo.graph
            plain = topo.name
            expected = EXPECTED_TOPOLOGY_SIZES.get(plain)
            if expected and (G.number_of_nodes(), G.number_of_edges()) != expected:
                log.warning(
                    "Topology '%s' has V=%d,E=%d; expected V=%d,E=%d "
                    "for the named benchmark. Results are not directly "
                    "comparable with the baseline paper.",
                    plain, G.number_of_nodes(), G.number_of_edges(),
                    expected[0], expected[1],
                )
            log.info(
                "Topology '%s': V=%d, E=%d",
                plain, G.number_of_nodes(), G.number_of_edges(),
            )
            traffic = gravity_traffic_matrix(G, seed=replicate_seed)

            lfc = compute_lfc_scheme(G)
            out_lfc = simulate_failures(
                G, lfc.next_hops, lfc.protected_links, traffic,
                num_trials=num_trials, seed=replicate_seed,
            )

            tbfh_nh = None
            dmpa_nh = None
            if include_extended_baselines:
                tbfh_nh = {c: compute_tbfh(G, c) for c in G.nodes()}
                dmpa_nh = {c: compute_dmpa_e(G, c) for c in G.nodes()}

            for B in budgets:
                hlp = compute_hlp(G, R=1.0, max_links=B)
                out_hlp = simulate_failures(
                    G, hlp.next_hops, hlp.protected_links, traffic,
                    num_trials=num_trials, seed=replicate_seed,
                )
                ta = compute_ta_hlp(G, traffic, R=None, max_links=B)
                out_ta = simulate_failures(
                    G, ta.next_hops, ta.protected_links, traffic,
                    num_trials=num_trials, seed=replicate_seed,
                )

                common = {
                    "replicate": replicate,
                    "replicate_seed": replicate_seed,
                    "topology": plain,
                    "node_count": G.number_of_nodes(),
                    "edge_count": G.number_of_edges(),
                    "budget": B,
                    "num_trials": num_trials,
                }
                rows.extend([
                    {
                        **common, "method": "LFC Only",
                        "topological_availability": out_lfc.topological_availability,
                        "traffic_availability": out_lfc.traffic_availability,
                        "packet_loss_proxy": out_lfc.packet_loss_proxy,
                        "backup_links": 0,
                        "compute_time_s": lfc.compute_time_s,
                    },
                    {
                        **common, "method": "HLP (Original)",
                        "topological_availability": out_hlp.topological_availability,
                        "traffic_availability": out_hlp.traffic_availability,
                        "packet_loss_proxy": out_hlp.packet_loss_proxy,
                        "backup_links": len(hlp.protected_links),
                        "compute_time_s": hlp.compute_time_s,
                    },
                    {
                        **common, "method": "TA-HLP (Proposed)",
                        "topological_availability": out_ta.topological_availability,
                        "traffic_availability": out_ta.traffic_availability,
                        "packet_loss_proxy": out_ta.packet_loss_proxy,
                        "backup_links": len(ta.protected_links),
                        "compute_time_s": ta.compute_time_s,
                    },
                ])

                if include_extended_baselines and tbfh_nh is not None:
                    out_tbfh = simulate_failures(
                        G, tbfh_nh, [], traffic,
                        num_trials=num_trials, seed=replicate_seed,
                    )
                    rows.append({
                        **common, "method": "TBFH",
                        "topological_availability": out_tbfh.topological_availability,
                        "traffic_availability": out_tbfh.traffic_availability,
                        "packet_loss_proxy": out_tbfh.packet_loss_proxy,
                        "backup_links": 0, "compute_time_s": 0.0,
                    })
                if include_extended_baselines and dmpa_nh is not None:
                    out_dmpa = simulate_failures(
                        G, dmpa_nh, [], traffic,
                        num_trials=num_trials, seed=replicate_seed,
                    )
                    rows.append({
                        **common, "method": "DMPA-e",
                        "topological_availability": out_dmpa.topological_availability,
                        "traffic_availability": out_dmpa.traffic_availability,
                        "packet_loss_proxy": out_dmpa.packet_loss_proxy,
                        "backup_links": 0, "compute_time_s": 0.0,
                    })

    df = pd.DataFrame(rows)
    out_file = os.path.join(out_dir, "all_topologies_raw.csv")
    df.to_csv(out_file, index=False)
    log.info("Saved consolidated results -> %s", out_file)

    summary = _summarize_results(df)
    summary.to_csv(os.path.join(out_dir, "all_topologies.csv"), index=False)
    log.info("Saved summary results -> %s", os.path.join(out_dir, "all_topologies.csv"))

    for plain in summary["topology"].unique():
        sub = summary[summary["topology"] == plain]
        sub_csv = os.path.join(out_dir, f"budget_sweep_{plain}.csv")
        sub.to_csv(sub_csv, index=False)
        log.info("Saved per-topology CSV -> %s", sub_csv)

    return df


def _summarize_results(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate replicate results with standard errors and 95% CIs."""
    group_cols = [
        "topology", "node_count", "edge_count", "budget", "method"
    ]
    metric_cols = [
        "topological_availability", "traffic_availability",
        "packet_loss_proxy", "backup_links", "compute_time_s",
    ]
    summary = df.groupby(group_cols)[metric_cols].agg(
        ["mean", "std", "count"]
    ).reset_index()
    summary.columns = [
        "_".join(part for part in column if part).rstrip("_")
        if isinstance(column, tuple) else column
        for column in summary.columns
    ]
    for metric in metric_cols:
        std = summary[f"{metric}_std"].fillna(0.0)
        count = summary[f"{metric}_count"].clip(lower=1)
        margin = 1.96 * std / count.pow(0.5)
        summary[f"{metric}_ci95"] = margin
    return summary


def cli() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--topologies", nargs="+", default=DEFAULT_TOPOS)
    ap.add_argument("--budgets", type=int, nargs="+", default=DEFAULT_BUDGETS)
    ap.add_argument("--trials", type=int, default=300)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--replicates", type=int, default=1,
                    help="Independent topology/traffic/failure repetitions.")
    ap.add_argument("--out", type=str, default=os.path.join(ROOT, "results"))
    ap.add_argument("--include-extended-baselines", action="store_true",
                    help="Also include TBFH and DMPA-e in the sweep (slower).")
    args = ap.parse_args()
    run_sweep(args.topologies, args.budgets, args.trials, args.seed, args.out,
              include_extended_baselines=args.include_extended_baselines,
              replicates=args.replicates)


if __name__ == "__main__":
    cli()
