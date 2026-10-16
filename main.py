"""Convenience entry-point. Runs the demo experiment then the budget sweep.

Examples
--------
    python main.py                                 # quick demo on synthetic graph
    python main.py --sweep                         # full sweep on Abilene only
    python main.py --sweep --topologies Abilene.gml Geant2012.gml Sprint.gml
    python main.py --sweep --tri-ls 300 --plot
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.abspath(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.append(ROOT)

from experiments.run_demo import main as run_demo
from experiments.run_budget_sweep import run_sweep
from plotting.plot_results import main as plot_main


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--topology", type=str, default=None,
                    help="GML file for the quick demo (default: synthetic BA graph)")
    ap.add_argument("--budget", type=int, default=6,
                    help="Backup-link budget for the demo")
    ap.add_argument("--sweep", action="store_true",
                    help="Run the full budget sweep across all configured topologies")
    ap.add_argument("--topologies", nargs="+",
                    default=["Abilene.gml", "Geant2012.gml", "Sprint.gml"])
    ap.add_argument("--budgets", type=int, nargs="+", default=[2, 4, 6, 8, 10, 12, 14, 16])
    ap.add_argument("--trials", type=int, default=300)
    ap.add_argument("--replicates", type=int, default=1,
                    help="Independent topology/traffic/failure repetitions.")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--plot", action="store_true",
                    help="Generate plots after running the sweep")
    ap.add_argument("--include-extended-baselines", action="store_true",
                    help="Also include TBFH and DMPA-e in the sweep (slower).")
    args = ap.parse_args()

    if args.sweep:
        out_dir = os.path.join(ROOT, "results")
        run_sweep(args.topologies, args.budgets, args.trials, args.seed, out_dir,
                  include_extended_baselines=args.include_extended_baselines,
                  replicates=args.replicates)
        if args.plot:
            # Reset sys.argv so plot_results' argparse doesn't pick up our flags.
            plot_main(argv=[])
    else:
        run_demo(args.topology, args.budget, args.trials, args.seed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
