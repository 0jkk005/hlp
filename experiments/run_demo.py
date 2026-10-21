"""Quick single-topology demo.

Runs LFC, HLP (MNP-e + BPP), and TA-HLP (MNP-e + TA-BPP) on one
topology with a fixed budget and prints their availability metrics.

Usage:
    python -m experiments.run_demo --topology data/gml/Abilene.gml --budget 8
    python -m experiments.run_demo                       # synthetic fallback
"""
from __future__ import annotations

import argparse
import os
import sys

# Make ``src`` importable as a package from any CWD.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.append(ROOT)

from src.topology import NetworkTopology
from src.traffic_matrix import gravity_traffic_matrix
from src.protection import compute_lfc_scheme, compute_hlp, compute_ta_hlp
from src.simulator import simulate_failures
from src.metrics import backup_overhead_ratio


def main(topology_path: str | None, budget: int, num_trials: int, seed: int) -> None:
    if topology_path:
        topo = NetworkTopology.from_gml(topology_path, seed=seed)
    else:
        print("[demo] No topology provided -> generating an explicitly synthetic graph (n=30, m=3)")
        topo = NetworkTopology.generate_random(n=30, m=3, seed=seed)

    G = topo.graph
    traffic = gravity_traffic_matrix(G, seed=seed)

    print("\n" + "=" * 72)
    print(topo.summary())
    print("=" * 72)

    # --- LFC baseline (no BPP) ---
    lfc = compute_lfc_scheme(G)
    out_lfc = simulate_failures(G, lfc.next_hops, lfc.protected_links, traffic,
                                num_trials=num_trials, seed=seed)
    print(f"\n[LFC Only]")
    print(f"  Topological Availability : {out_lfc.topological_availability:.4f}")
    print(f"  Traffic    Availability  : {out_lfc.traffic_availability:.4f}")
    print(f"  Overhead (BPP links)     : 0")
    print(f"  Compute Time (s)         : {lfc.compute_time_s:.3f}")

    # --- Original HLP (MNP-e + BPP), no budget cap ---
    hlp = compute_hlp(G, R=1.0)  # R=1 forces protecting as many links as Δ > 0
    out_hlp_full = simulate_failures(G, hlp.next_hops, hlp.protected_links, traffic,
                                     num_trials=num_trials, seed=seed)
    print(f"\n[HLP Full (no budget)]")
    print(f"  Topological Availability : {out_hlp_full.topological_availability:.4f}")
    print(f"  Traffic    Availability  : {out_hlp_full.traffic_availability:.4f}")
    print(f"  Overhead (BPP links)     : {len(hlp.protected_links)} "
          f"({backup_overhead_ratio(G, hlp.protected_links)*100:.2f}%)")
    print(f"  Compute Time (s)         : {hlp.compute_time_s:.3f}")

    # --- HLP with budget ---
    hlp_b = compute_hlp(G, R=1.0, max_links=budget)
    out_hlp_b = simulate_failures(G, hlp_b.next_hops, hlp_b.protected_links, traffic,
                                  num_trials=num_trials, seed=seed)
    print(f"\n[HLP Budget={budget}]")
    print(f"  Topological Availability : {out_hlp_b.topological_availability:.4f}")
    print(f"  Traffic    Availability  : {out_hlp_b.traffic_availability:.4f}")
    print(f"  Overhead (BPP links)     : {len(hlp_b.protected_links)}")

    # --- TA-HLP (our method), budget enforced ---
    ta = compute_ta_hlp(G, traffic, R=None, max_links=budget)
    out_ta = simulate_failures(G, ta.next_hops, ta.protected_links, traffic,
                               num_trials=num_trials, seed=seed)
    print(f"\n[TA-HLP Budget={budget}  (ours)]")
    print(f"  Topological Availability : {out_ta.topological_availability:.4f}")
    print(f"  Traffic    Availability  : {out_ta.traffic_availability:.4f}")
    print(f"  Overhead (BPP links)     : {len(ta.protected_links)}")
    print(f"  Compute Time (s)         : {ta.compute_time_s:.3f}")
    print(f"  MNP-e recoveries         : {out_ta.mnp_recovery_count}")
    print(f"  BPP  recoveries          : {out_ta.bpp_recovery_count}")
    print()


def cli() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--topology", type=str, default=None,
                    help="GML file (or None to use a synthetic 30-node BA graph)")
    ap.add_argument("--budget", type=int, default=8,
                    help="Maximum number of BPP/TA-BPP links")
    ap.add_argument("--trials", type=int, default=300,
                    help="Number of Monte Carlo failure trials")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    main(args.topology, args.budget, args.trials, args.seed)


if __name__ == "__main__":
    cli()
