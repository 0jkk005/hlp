"""Statistical & Ablation Experiment Runner for TA-HLP Paper.

This script runs comprehensive experiments with:
- Synthetic size-matched topologies (matching Rocketfuel paper V/E counts from Geng et al. 2020 Table 3)
  Note: Real Rocketfuel .cch/.edgelist files from CAIDA are not included. Pipeline falls back to
  reproducible synthetic BA graphs. For exact structural reproduction, place Rocketfuel files in data/rocketfuel/.
- Multiple independent replicates (≥5) for statistical significance
- Paired one-sided t-tests between HLP and TA-HLP with Bonferroni correction
- Effect size calculations (Cohen's d) and 95% CIs
- Ablation studies (randomized traffic weights, uniform traffic)
- Verification of "never underperforms" claim across all raw cells
- Publication-ready CSV outputs with statistical annotations and environment metadata
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import random
import sys
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.append(ROOT)

from src.rocketfuel import load_rocketfuel
from src.topology import NetworkTopology
from src.protection import compute_lfc_scheme, compute_hlp, compute_ta_hlp
from src.simulator import simulate_failures
from src.utils import ensure_dir, get_logger

log = get_logger("stat_exp")

# ============================================================
# Prespecified Statistical Protocol
# ============================================================
# HYPOTHESIS (one-sided, prespecified):
# H0: TA-HLP traffic availability <= HLP traffic availability
# H1: TA-HLP traffic availability > HLP traffic availability
# Test: paired one-sided t-test across replicates
# Alpha: 0.05
# Correction: Bonferroni across (topologies × budgets × metrics) comparisons
# Effect size: Cohen's d for paired samples
# CI: 95% CI for difference using t-distribution
# ============================================================

# Rocketfuel topologies matching Geng et al. 2020 Table 3 (synthetic size-matched)
ROCKETFUEL_TOPOS = {
    "Exodus":   (79,  147),
    "Telstra":  (108, 153),
    "Tiscali":  (161, 328),
    "Sprint315": (315, 972),
}

DEFAULT_BUDGETS = [2, 4, 6, 8, 10, 12, 14, 16]
DEFAULT_TRIALS = 100
DEFAULT_REPLICATES = 5
DEFAULT_SEED = 42
ALPHA = 0.05


# ============================================================
# Traffic Matrix Variants for Ablation
# ============================================================

from src.traffic_matrix import gravity_traffic_matrix



def uniform_traffic_matrix(
    graph, scale: float = 1.0, seed: Optional[int] = None
) -> Dict[Tuple[int, int], float]:
    """Uniform traffic matrix (all pairs equal) - ablation baseline."""
    T = {}
    nodes = list(graph.nodes())
    n = len(nodes)
    for s in nodes:
        for d in nodes:
            if s == d:
                continue
            T[(s, d)] = scale
    return T


def randomized_traffic_matrix(
    graph, scale: float = 1.0, seed: Optional[int] = None
) -> Dict[Tuple[int, int], float]:
    """Randomized traffic matrix (uniform random) - ablation to test if gravity structure matters."""
    import random
    rng = random.Random(seed)
    T = {}
    nodes = list(graph.nodes())
    for s in nodes:
        for d in nodes:
            if s == d:
                continue
            T[(s, d)] = scale * rng.uniform(0.1, 10.0)
    return T


TRAFFIC_MATRIX_VARIANTS = {
    "gravity": gravity_traffic_matrix,
    "uniform": uniform_traffic_matrix,
    "randomized": randomized_traffic_matrix,
}


# ============================================================
# Data Structures
# ============================================================

@dataclass
class ExperimentResult:
    """Single experimental cell result."""
    replicate: int
    replicate_seed: int
    topology: str
    topology_type: str  # "rocketfuel_synthetic"
    node_count: int
    edge_count: int
    budget: int
    method: str  # "LFC Only", "HLP (Original)", "TA-HLP (Proposed)"
    num_trials: int
    topological_availability: float
    traffic_availability: float
    packet_loss_proxy: float
    backup_links: int
    compute_time_s: float
    mnp_recovery_count: int = 0
    bpp_recovery_count: int = 0


@dataclass
class StatisticalComparison:
    """Paired statistical comparison between two methods."""
    topology: str
    budget: int
    metric: str  # "topological_availability" or "traffic_availability"
    method_a: str
    method_b: str
    mean_a: float
    mean_b: float
    std_a: float
    std_b: float
    n: int
    t_statistic: float
    p_value: float
    p_value_bonferroni: float
    wilcoxon_w: float = 0.0
    wilcoxon_p: float = 1.0
    wilcoxon_p_bonferroni: float = 1.0
    cohens_d: float = 0.0
    ci95_diff: Tuple[float, float] = (0.0, 0.0)  # 95% CI for difference (b - a)
    significant_at_05: bool = False
    significant_at_01: bool = False
    significant_bonferroni: bool = False



@dataclass
class NeverUnderperformsCheck:
    """Verification of 'TA-HLP never underperforms HLP' claim."""
    topology: str
    budget: int
    metric: str
    all_ta_ge_hlp: bool  # True if every replicate has TA-HLP >= HLP
    min_delta: float     # minimum (TA-HLP - HLP) across replicates
    max_delta: float     # maximum (TA-HLP - HLP) across replicates
    n_replicates: int


# ============================================================
# Core Experiment Functions
# ============================================================

def run_single_configuration(
    graph,
    traffic: Dict[Tuple[int, int], float],
    budget: int,
    num_trials: int,
    seed: int,
) -> Dict[str, ExperimentResult]:
    """Run all three methods on one topology/budget/traffic configuration."""
    results = {}
    
    # LFC Only (baseline)
    lfc = compute_lfc_scheme(graph)
    out_lfc = simulate_failures(
        graph, lfc.next_hops, lfc.protected_links, traffic,
        num_trials=num_trials, seed=seed,
    )
    results["LFC Only"] = ExperimentResult(
        replicate=0, replicate_seed=seed, topology="", topology_type="",
        node_count=graph.number_of_nodes(), edge_count=graph.number_of_edges(),
        budget=budget, method="LFC Only", num_trials=num_trials,
        topological_availability=out_lfc.topological_availability,
        traffic_availability=out_lfc.traffic_availability,
        packet_loss_proxy=out_lfc.packet_loss_proxy,
        backup_links=0, compute_time_s=lfc.compute_time_s,
        mnp_recovery_count=out_lfc.mnp_recovery_count,
        bpp_recovery_count=out_lfc.bpp_recovery_count,
    )
    
    # HLP Original
    hlp = compute_hlp(graph, R=1.0, max_links=budget)
    out_hlp = simulate_failures(
        graph, hlp.next_hops, hlp.protected_links, traffic,
        num_trials=num_trials, seed=seed,
    )
    results["HLP (Original)"] = ExperimentResult(
        replicate=0, replicate_seed=seed, topology="", topology_type="",
        node_count=graph.number_of_nodes(), edge_count=graph.number_of_edges(),
        budget=budget, method="HLP (Original)", num_trials=num_trials,
        topological_availability=out_hlp.topological_availability,
        traffic_availability=out_hlp.traffic_availability,
        packet_loss_proxy=out_hlp.packet_loss_proxy,
        backup_links=len(hlp.protected_links), compute_time_s=hlp.compute_time_s,
        mnp_recovery_count=out_hlp.mnp_recovery_count,
        bpp_recovery_count=out_hlp.bpp_recovery_count,
    )
    
    # TA-HLP
    ta = compute_ta_hlp(graph, traffic, R=None, max_links=budget)
    out_ta = simulate_failures(
        graph, ta.next_hops, ta.protected_links, traffic,
        num_trials=num_trials, seed=seed,
    )
    results["TA-HLP (Proposed)"] = ExperimentResult(
        replicate=0, replicate_seed=seed, topology="", topology_type="",
        node_count=graph.number_of_nodes(), edge_count=graph.number_of_edges(),
        budget=budget, method="TA-HLP (Proposed)", num_trials=num_trials,
        topological_availability=out_ta.topological_availability,
        traffic_availability=out_ta.traffic_availability,
        packet_loss_proxy=out_ta.packet_loss_proxy,
        backup_links=len(ta.protected_links), compute_time_s=ta.compute_time_s,
        mnp_recovery_count=out_ta.mnp_recovery_count,
        bpp_recovery_count=out_ta.bpp_recovery_count,
    )
    
    return results


def run_replicate(
    topo_name: str,
    topo_type: str,
    budgets: List[int],
    num_trials: int,
    replicate_idx: int,
    base_seed: int,
    traffic_variant: str = "gravity",
) -> List[ExperimentResult]:
    """Run one complete replicate across all budgets for a topology."""
    replicate_seed = base_seed + replicate_idx * 1000
    
    # Load topology
    if topo_type == "sndlib":
        from src.sndlib import load_sndlib
        graph, traffic = load_sndlib(topo_name, seed=replicate_seed)
        if traffic_variant != "gravity":
            traffic_fn = TRAFFIC_MATRIX_VARIANTS[traffic_variant]
            traffic = traffic_fn(graph, seed=replicate_seed)
    elif topo_type == "rocketfuel":
        graph = load_rocketfuel(topo_name, seed=replicate_seed)
        traffic_fn = TRAFFIC_MATRIX_VARIANTS[traffic_variant]
        traffic = traffic_fn(graph, seed=replicate_seed)
    else:
        path = os.path.join(ROOT, "data", "gml", f"{topo_name}.gml")
        if os.path.exists(path):
            graph = NetworkTopology.from_gml(path, seed=replicate_seed).graph
        else:
            n, m_target = ROCKETFUEL_TOPOS.get(topo_name, (50, 3))
            m_ba = max(1, min(n - 1, int(round(m_target / n))))
            graph = NetworkTopology.generate_random(n=n, m=m_ba, seed=replicate_seed, name=topo_name).graph
            while graph.number_of_edges() < m_target:
                u = random.choice(list(graph.nodes()))
                v = random.choice(list(graph.nodes()))
                if u != v and not graph.has_edge(u, v):
                    graph.add_edge(u, v)
            while graph.number_of_edges() > m_target:
                e = random.choice(list(graph.edges()))
                graph.remove_edge(*e)
        traffic_fn = TRAFFIC_MATRIX_VARIANTS[traffic_variant]
        traffic = traffic_fn(graph, seed=replicate_seed)

    log.info("Replicate %d/%s: %s (V=%d, E=%d, traffic=%s)",
             replicate_idx, topo_name, topo_type, graph.number_of_nodes(),
             graph.number_of_edges(), traffic_variant)
    
    all_results = []
    for budget in budgets:
        cell_results = run_single_configuration(
            graph, traffic, budget, num_trials, replicate_seed + budget
        )
        for method, result in cell_results.items():
            result.replicate = replicate_idx
            result.replicate_seed = replicate_seed + budget
            result.topology = topo_name
            result.topology_type = topo_type
            all_results.append(result)
    
    return all_results


def run_experiment(
    topologies: Dict[str, Tuple[int, int]],
    topo_type: str,
    budgets: List[int],
    num_trials: int,
    replicates: int,
    base_seed: int,
    traffic_variant: str = "gravity",
) -> List[ExperimentResult]:
    """Run full experiment across topologies and replicates."""
    all_results = []
    
    for topo_name in topologies:
        for rep in range(replicates):
            rep_results = run_replicate(
                topo_name, topo_type, budgets, num_trials,
                rep, base_seed, traffic_variant
            )
            all_results.extend(rep_results)
    
    return all_results


def compute_statistics(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[StatisticalComparison], List[NeverUnderperformsCheck]]:
    """Compute summary statistics, paired comparisons, and 'never underperforms' verification."""
    
    # Summary statistics (mean, std, count, CI95)
    group_cols = ["topology", "topology_type", "node_count", "edge_count", "budget", "method"]
    metric_cols = [
        "topological_availability", "traffic_availability",
        "packet_loss_proxy", "backup_links", "compute_time_s",
        "mnp_recovery_count", "bpp_recovery_count",
    ]
    
    summary = df.groupby(group_cols)[metric_cols].agg(
        ["mean", "std", "count"]
    ).reset_index()
    summary.columns = [
        "_".join(part for part in column if part).rstrip("_")
        if isinstance(column, tuple) else column
        for column in summary.columns
    ]
    
    # Add CI95 using t-distribution
    for metric in metric_cols:
        std_col = f"{metric}_std"
        count_col = f"{metric}_count"
        if std_col in summary.columns and count_col in summary.columns:
            std = summary[std_col].fillna(0.0)
            count = summary[count_col].clip(lower=1)
            margins = []
            for sample_std, sample_count in zip(std, count):
                if sample_count > 1 and sample_std > 0:
                    critical = stats.t.ppf(0.975, int(sample_count) - 1)
                    margins.append(critical * sample_std / np.sqrt(sample_count))
                else:
                    margins.append(0.0)
            margin = pd.Series(margins, index=summary.index)
            summary[f"{metric}_ci95"] = margin
    
    # Paired statistical comparisons: HLP vs TA-HLP
    comparisons = []
    for topology in df["topology"].unique():
        for budget in df["budget"].unique():
            for metric in ["topological_availability", "traffic_availability"]:
                sub = df[(df["topology"] == topology) & (df["budget"] == budget)]
                
                hlp_vals = sub[sub["method"] == "HLP (Original)"][metric].values
                ta_vals = sub[sub["method"] == "TA-HLP (Proposed)"][metric].values
                
                if len(hlp_vals) >= 2 and len(ta_vals) >= 2 and len(hlp_vals) == len(ta_vals):
                    # Paired one-sided t-test
                    t_stat, p_val = stats.ttest_rel(ta_vals, hlp_vals, alternative='greater')

                    # Non-parametric Wilcoxon signed-rank test (one-sided)
                    diff = ta_vals - hlp_vals
                    if np.all(np.abs(diff) < 1e-12):
                        w_stat, p_val_w = 0.0, 1.0
                    else:
                        try:
                            res_w = stats.wilcoxon(ta_vals, hlp_vals, alternative='greater')
                            w_stat, p_val_w = float(res_w.statistic), float(res_w.pvalue)
                        except Exception:
                            w_stat, p_val_w = 0.0, 1.0

                    # Cohen's d for paired samples
                    cohens_d = np.mean(diff) / (np.std(diff, ddof=1) + 1e-10)

                    # 95% CI for difference using t-distribution
                    mean_diff = np.mean(diff)
                    se_diff = np.std(diff, ddof=1) / np.sqrt(len(diff))
                    critical = stats.t.ppf(0.975, len(diff) - 1)
                    ci_low = mean_diff - critical * se_diff
                    ci_high = mean_diff + critical * se_diff

                    # Bonferroni correction
                    # Number of comparisons = n_topologies × n_budgets × n_metrics
                    n_topologies = df["topology"].nunique()
                    n_budgets = df["budget"].nunique()
                    n_metrics = 2  # topological_availability, traffic_availability
                    n_comparisons = n_topologies * n_budgets * n_metrics
                    p_val_bonf = min(1.0, p_val * n_comparisons)
                    p_val_w_bonf = min(1.0, p_val_w * n_comparisons)

                    comparisons.append(StatisticalComparison(
                        topology=topology,
                        budget=budget,
                        metric=metric,
                        method_a="HLP (Original)",
                        method_b="TA-HLP (Proposed)",
                        mean_a=np.mean(hlp_vals),
                        mean_b=np.mean(ta_vals),
                        std_a=np.std(hlp_vals, ddof=1),
                        std_b=np.std(ta_vals, ddof=1),
                        n=len(hlp_vals),
                        t_statistic=t_stat,
                        p_value=p_val,
                        p_value_bonferroni=p_val_bonf,
                        wilcoxon_w=w_stat,
                        wilcoxon_p=p_val_w,
                        wilcoxon_p_bonferroni=p_val_w_bonf,
                        cohens_d=cohens_d,
                        ci95_diff=(ci_low, ci_high),
                        significant_at_05=p_val < 0.05,
                        significant_at_01=p_val < 0.01,
                        significant_bonferroni=p_val_bonf < 0.05,
                    ))
    
    # Verify "never underperforms" claim across ALL raw cells
    never_underperforms = []
    for topology in df["topology"].unique():
        for budget in df["budget"].unique():
            for metric in ["topological_availability", "traffic_availability"]:
                sub = df[(df["topology"] == topology) & (df["budget"] == budget)]
                
                hlp_vals = sub[sub["method"] == "HLP (Original)"][metric].values
                ta_vals = sub[sub["method"] == "TA-HLP (Proposed)"][metric].values
                
                if len(hlp_vals) >= 1 and len(ta_vals) >= 1 and len(hlp_vals) == len(ta_vals):
                    deltas = ta_vals - hlp_vals
                    all_ge = np.all(deltas >= -1e-10)  # allow tiny numerical noise
                    never_underperforms.append(NeverUnderperformsCheck(
                        topology=topology,
                        budget=budget,
                        metric=metric,
                        all_ta_ge_hlp=bool(all_ge),
                        min_delta=float(np.min(deltas)),
                        max_delta=float(np.max(deltas)),
                        n_replicates=len(deltas),
                    ))
    
    return summary, comparisons, never_underperforms


def capture_environment_metadata() -> Dict:
    """Capture execution environment metadata for reproducibility."""
    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
        "scipy_version": stats.__name__ if hasattr(stats, '__version__') else "unknown",
        "networkx_version": None,  # filled below if available
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "command_line": " ".join(sys.argv),
    }


def save_results(
    raw_results: List[ExperimentResult],
    summary: pd.DataFrame,
    comparisons: List[StatisticalComparison],
    never_underperforms: List[NeverUnderperformsCheck],
    out_dir: str,
    env_meta: Dict,
    prefix: str = "",
) -> None:
    """Save all results to CSV files plus environment metadata."""
    ensure_dir(out_dir)
    
    # Raw results
    raw_df = pd.DataFrame([asdict(r) for r in raw_results])
    raw_df.to_csv(os.path.join(out_dir, f"{prefix}all_topologies_raw.csv"), index=False)
    
    # Summary with statistics
    summary.to_csv(os.path.join(out_dir, f"{prefix}all_topologies_summary.csv"), index=False)
    
    # Statistical comparisons
    comp_df = pd.DataFrame([asdict(c) for c in comparisons])
    comp_df.to_csv(os.path.join(out_dir, f"{prefix}statistical_comparisons.csv"), index=False)
    
    # Never underperforms verification
    never_df = pd.DataFrame([asdict(c) for c in never_underperforms])
    never_df.to_csv(os.path.join(out_dir, f"{prefix}never_underperforms.csv"), index=False)
    
    # Per-topology CSVs
    for topo in summary["topology"].unique():
        sub = summary[summary["topology"] == topo]
        sub.to_csv(os.path.join(out_dir, f"{prefix}budget_sweep_{topo}.csv"), index=False)
    
    # Environment metadata
    with open(os.path.join(out_dir, f"{prefix}environment_metadata.json"), "w") as f:
        json.dump(env_meta, f, indent=2)
    
    log.info("Saved results to %s", out_dir)


def print_statistical_summary(comparisons: List[StatisticalComparison], never_underperforms: List[NeverUnderperformsCheck]) -> None:
    """Print formatted statistical comparison results."""
    print("\n" + "="*115)
    print("STATISTICAL COMPARISONS: C-TA-HLP vs HLP (Original) — Paired t-tests & Wilcoxon Signed-Rank Tests")
    print("="*115)
    print(f"{'Topology':<12} {'Budget':>5} {'Metric':<18} {'Delta Mean':>10} {'t-stat':>7} {'p-t':>9} {'p-bonf':>9} {'W-stat':>7} {'p-wilc':>9} {'d':>5} {'Sig':>4}")
    print("-"*115)
    
    for c in comparisons:
        sig = "***" if c.significant_at_01 else ("*" if c.significant_at_05 else "ns")
        delta = c.mean_b - c.mean_a
        metric_short = "Topo.Avail" if c.metric == "topological_availability" else "Traffic.Avail"
        print(f"{c.topology:<12} {c.budget:>5} {metric_short:<18} {delta:>10.6f} {c.t_statistic:>7.2f} {c.p_value:>9.4f} {c.p_value_bonferroni:>9.4f} {c.wilcoxon_w:>7.1f} {c.wilcoxon_p:>9.4f} {c.cohens_d:>5.2f} {sig:>4}")

    
    # Summary
    sig_05 = sum(1 for c in comparisons if c.significant_at_05)
    sig_01 = sum(1 for c in comparisons if c.significant_at_01)
    sig_bonf = sum(1 for c in comparisons if c.significant_bonferroni)
    total = len(comparisons)
    print(f"\nSignificant at alpha=0.05 (uncorrected): {sig_05}/{total}")
    print(f"Significant at alpha=0.01 (uncorrected): {sig_01}/{total}")
    print(f"Significant after Bonferroni correction: {sig_bonf}/{total}")
    
    # Per-topology summary
    print("\nPer-topology traffic availability advantage (TA-HLP - HLP):")
    for topo in set(c.topology for c in comparisons):
        topo_comps = [c for c in comparisons if c.topology == topo and c.metric == "traffic_availability"]
        if topo_comps:
            avg_delta = np.mean([c.mean_b - c.mean_a for c in topo_comps])
            sig_count = sum(1 for c in topo_comps if c.significant_at_05)
            bonf_count = sum(1 for c in topo_comps if c.significant_bonferroni)
            print(f"  {topo}: avg Delta = {avg_delta:.6f}, sig uncorrected {sig_count}/{len(topo_comps)}, sig Bonferroni {bonf_count}/{len(topo_comps)}")
    
    # Never underperforms verification
    print("\n" + "="*80)
    print("VERIFICATION: 'TA-HLP never underperforms HLP' claim")
    print("="*80)
    print(f"{'Topology':<12} {'Budget':>5} {'Metric':<25} {'All TA>=HLP':>10} {'Min Delta':>12} {'Max Delta':>12} {'Reps':>4}")
    print("-"*80)
    all_true = True
    for c in never_underperforms:
        status = "TRUE" if c.all_ta_ge_hlp else "FALSE"
        if not c.all_ta_ge_hlp:
            all_true = False
        metric_short = "Topo.Avail" if c.metric == "topological_availability" else "Traffic.Avail"
        print(f"{c.topology:<12} {c.budget:>5} {metric_short:<25} {status:>10} {c.min_delta:>12.6f} {c.max_delta:>12.6f} {c.n_replicates:>4}")
    print(f"\nOverall claim holds: {all_true}")


# ============================================================
# CLI
# ============================================================

SNDLIB_TOPOS = {
    "abilene": (12, 15),
    "geant": (22, 36),
    "germany50": (50, 88),
    "nobel-eu": (28, 41),
}


def cli() -> None:
    ap = argparse.ArgumentParser(description="Full Statistical TA-HLP Experiments")
    ap.add_argument("--topologies", nargs="+", default=None,
                    help="Topology names")
    ap.add_argument("--topo-type", choices=["rocketfuel", "sndlib", "gml"], default="rocketfuel")
    ap.add_argument("--budgets", type=int, nargs="+", default=DEFAULT_BUDGETS)
    ap.add_argument("--trials", type=int, default=DEFAULT_TRIALS)
    ap.add_argument("--replicates", type=int, default=DEFAULT_REPLICATES)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--out", type=str, default=os.path.join(ROOT, "results_full"))
    ap.add_argument("--traffic-variant", choices=list(TRAFFIC_MATRIX_VARIANTS.keys()), default="gravity")
    ap.add_argument("--run-ablation", action="store_true",
                    help="Run ablation with all traffic matrix variants")
    args = ap.parse_args()
    
    # Determine topologies to use
    if args.topo_type == "sndlib":
        available = list(SNDLIB_TOPOS.keys())
        selected = [t for t in available if t in args.topologies] if args.topologies else available
        topo_dict = {t: SNDLIB_TOPOS[t] for t in selected}
    elif args.topo_type == "rocketfuel":
        available = list(ROCKETFUEL_TOPOS.keys())
        selected = [t for t in available if t in args.topologies] if args.topologies else available
        topo_dict = {t: ROCKETFUEL_TOPOS[t] for t in selected}
    else:
        selected = args.topologies or ["Abilene", "Geant2012"]
        topo_dict = {t: (30, 45) for t in selected}
    
    env_meta = capture_environment_metadata()
    all_results = []
    
    # Main experiment
    if topo_dict:
        log.info("Running main experiment on %s topologies (%s)...", args.topo_type, list(topo_dict.keys()))
        results = run_experiment(
            topo_dict, args.topo_type, args.budgets, args.trials, args.replicates,
            args.seed, args.traffic_variant
        )
        all_results.extend(results)
    
    # Ablation experiments
    if args.run_ablation:
        for variant in ["uniform", "randomized"]:
            log.info("Running ablation with traffic variant: %s", variant)
            if topo_dict:
                results = run_experiment(
                    topo_dict, args.topo_type, args.budgets, args.trials, args.replicates,
                    args.seed + 10000, variant
                )
                all_results.extend(results)
    
    # Compute statistics
    df = pd.DataFrame([asdict(r) for r in all_results])
    summary, comparisons, never_underperforms = compute_statistics(df)
    
    # Save results
    save_results(all_results, summary, comparisons, never_underperforms, args.out, env_meta)
    
    # Print summary
    print_statistical_summary(comparisons, never_underperforms)
    
    print(f"\nResults saved to: {args.out}")


if __name__ == "__main__":
    cli()