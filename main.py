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
    ap.add_argument("--complete-run", action="store_true",
                    help="Run the complete publication benchmark campaign in a single unified run")
    args = ap.parse_args()

    results_dir = os.path.join(ROOT, "results")
    if args.complete_run:
        run_complete_campaign(
            budgets=[2, 4, 6, 8],
            trials=args.trials if args.trials != 300 else 500,
            replicates=args.replicates if args.replicates != 1 else 5,
            seed=args.seed,
            results_dir=results_dir,
        )
    elif args.sweep:
        run_sweep(args.topologies, args.budgets, args.trials, args.seed, results_dir,
                  include_extended_baselines=args.include_extended_baselines,
                  replicates=args.replicates)
        if args.plot:
            # Reset sys.argv so plot_results' argparse doesn't pick up our flags.
            plot_main(argv=[])
    else:
        run_demo(args.topology, args.budget, args.trials, args.seed)
    return 0


def run_complete_campaign(
    budgets: list[int] = [2, 4, 6, 8],
    trials: int = 500,
    replicates: int = 5,
    seed: int = 42,
    results_dir: str = os.path.join(ROOT, "results"),
) -> None:
    """Run the complete publication benchmark campaign in a single unified run."""
    print("=" * 110)
    print("STARTING COMPLETE EVALUATION CAMPAIGN (SINGLE UNIFIED RUN)")
    print("=" * 110)

    # 1. Canonical SNDlib NetFlow statistical campaign
    print("\n[Phase 1/4] Running Canonical SNDlib NetFlow Statistical Experiments...")
    from dataclasses import asdict
    import pandas as pd
    from experiments.run_statistical_experiments import (
        SNDLIB_TOPOS, run_experiment, compute_statistics,
        save_results, capture_environment_metadata, print_statistical_summary
    )
    sndlib_out = os.path.join(results_dir, "sndlib")
    os.makedirs(sndlib_out, exist_ok=True)
    raw_results = run_experiment(
        topologies=SNDLIB_TOPOS,
        topo_type="sndlib",
        budgets=budgets,
        num_trials=trials,
        replicates=replicates,
        base_seed=seed,
    )
    raw_df = pd.DataFrame([asdict(r) for r in raw_results])
    summary, comparisons, never_underperforms = compute_statistics(raw_df)
    meta = capture_environment_metadata()
    save_results(raw_results, summary, comparisons, never_underperforms, sndlib_out, meta)
    print_statistical_summary(comparisons, never_underperforms)

    # 2. Base Paper Table 3 & Table 4 Reproduction
    print("\n[Phase 2/4] Running Base Paper Compute-Time & Availability Reproduction (Tables 3 & 4)...")
    from experiments.run_table_reproduction import run_table3, run_table4
    topos_table = ["Abilene", "Exodus", "Telstra"]
    run_table3(topologies=topos_table, repeat=3, out_dir=results_dir)
    run_table4(topologies=topos_table, num_trials=trials, seed=seed, out_dir=results_dir)

    # 3. Budget sweep across baseline topologies
    print("\n[Phase 3/4] Running Benchmark Budget Sweep across Topology Zoo GMLs...")
    run_sweep(
        topologies=["Abilene.gml", "Geant2012.gml", "Sprint.gml"],
        budgets=[2, 4, 6, 8, 10, 12, 14, 16],
        num_trials=trials,
        seed=seed,
        out_dir=results_dir,
        include_extended_baselines=False,
        replicates=1,
    )

    # 4. Publication and diagnostic plotting
    print("\n[Phase 4/4] Generating Publication Figures and Summary Plots...")
    from plotting.plot_results import main as plot_results_main
    from plotting.plot_table_reproduction import main as plot_tables_main
    plots_dir = os.path.join(ROOT, "plots")
    plot_results_main(argv=["--results-dir", results_dir, "--plots-dir", plots_dir])
    plot_tables_main(argv=["--results-dir", results_dir, "--plots-dir", plots_dir])

    print("\n" + "=" * 110)
    print(f"SUCCESS! Complete evaluation campaign finished. All outputs stored in: {results_dir}")
    print("=" * 110)


if __name__ == "__main__":
    raise SystemExit(main())
