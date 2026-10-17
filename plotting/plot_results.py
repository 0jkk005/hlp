"""Generate publication-ready plots from ``results/all_topologies.csv``.

Produces:
    plots/traffic_avail_vs_budget_<TOPO>.png   (paper main figure)
    plots/topo_avail_vs_budget_<TOPO>.png
    plots/compute_time.png
    plots/bpp_vs_R.png
"""
from __future__ import annotations

import argparse
import os
import sys

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.append(ROOT)

from src.utils import ensure_dir

sns.set_theme(style="whitegrid", context="paper", font_scale=1.0)


METHOD_ORDER = ["LFC Only", "TBFH", "DMPA-e", "HLP (Original)", "TA-HLP (Proposed)"]
METHOD_COLORS = {
    "LFC Only": "tab:gray",
    "TBFH": "tab:green",
    "DMPA-e": "tab:brown",
    "HLP (Original)": "tab:blue",
    "TA-HLP (Proposed)": "tab:red",
}


def _ensure_method_order(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["method"] = pd.Categorical(df["method"], categories=METHOD_ORDER, ordered=True)
    return df.sort_values(["topology", "method", "budget"])


def _metric_column(df: pd.DataFrame, metric: str) -> str:
    """Return the raw or aggregated column name for a plotted metric."""
    mean_column = f"{metric}_mean"
    if mean_column in df.columns:
        return mean_column
    if metric in df.columns:
        return metric
    raise KeyError(f"Results do not contain '{metric}' or '{mean_column}'")


def _ci_column(df: pd.DataFrame, metric: str) -> str | None:
    column = f"{metric}_ci95"
    return column if column in df.columns else None


def plot_traffic_avail(df: pd.DataFrame, out_dir: str) -> None:
    """Main paper figure: Traffic Availability vs backup-link budget."""
    ensure_dir(out_dir)
    df = _ensure_method_order(df)
    metric = _metric_column(df, "traffic_availability")
    ci_metric = _ci_column(df, "traffic_availability")
    for topo in df["topology"].unique():
        sub = df[df["topology"] == topo]
        fig, ax = plt.subplots(figsize=(7.0, 4.2))
        for method in METHOD_ORDER:
            sub_m = sub[sub["method"] == method]
            if sub_m.empty:
                continue
            ax.plot(sub_m["budget"], sub_m[metric],
                    marker="o", linewidth=2, label=str(method),
                    color=METHOD_COLORS.get(str(method)))
            if ci_metric is not None:
                ax.fill_between(
                    sub_m["budget"],
                    sub_m[metric] - sub_m[ci_metric],
                    sub_m[metric] + sub_m[ci_metric],
                    color=METHOD_COLORS.get(str(method)),
                    alpha=0.12,
                )
        ax.set_title(f"Traffic Availability vs. Backup-Link Budget ({topo})")
        ax.set_xlabel("Max BPP links (B)")
        ax.set_ylabel(r"Traffic Availability  $T_A(G)$")
        ax.set_ylim(bottom=min(0.80, sub[metric].min() - 0.01),
                    top=min(1.001, sub[metric].max() + 0.02))
        ax.legend(loc="lower right")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        out_png = os.path.join(out_dir, f"traffic_avail_vs_budget_{topo}.png")
        out_pdf = os.path.join(out_dir, f"traffic_avail_vs_budget_{topo}.pdf")
        fig.savefig(out_png, dpi=300)
        fig.savefig(out_pdf, format="pdf", bbox_inches="tight")
        plt.close(fig)
        print(f"  saved -> {out_png} and {out_pdf}")


def plot_topo_avail(df: pd.DataFrame, out_dir: str) -> None:
    df = _ensure_method_order(df)
    metric = _metric_column(df, "topological_availability")
    ci_metric = _ci_column(df, "topological_availability")
    for topo in df["topology"].unique():
        sub = df[df["topology"] == topo]
        fig, ax = plt.subplots(figsize=(7.0, 4.2))
        for method in METHOD_ORDER:
            sub_m = sub[sub["method"] == method]
            if sub_m.empty:
                continue
            ax.plot(sub_m["budget"], sub_m[metric],
                    marker="s", linewidth=2, linestyle="--",
                    label=str(method), color=METHOD_COLORS.get(str(method)))
            if ci_metric is not None:
                ax.fill_between(
                    sub_m["budget"],
                    sub_m[metric] - sub_m[ci_metric],
                    sub_m[metric] + sub_m[ci_metric],
                    color=METHOD_COLORS.get(str(method)),
                    alpha=0.12,
                )
        ax.set_title(f"Topological Availability vs. Backup-Link Budget ({topo})")
        ax.set_xlabel("Max BPP links (B)")
        ax.set_ylabel(r"Topological Availability $A(G)$")
        ax.legend(loc="lower right")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        out_png = os.path.join(out_dir, f"topo_avail_vs_budget_{topo}.png")
        out_pdf = os.path.join(out_dir, f"topo_avail_vs_budget_{topo}.pdf")
        fig.savefig(out_png, dpi=300)
        fig.savefig(out_pdf, format="pdf", bbox_inches="tight")
        plt.close(fig)
        print(f"  saved -> {out_png} and {out_pdf}")


def plot_compute_time(csv_path: str, out_dir: str) -> None:
    if not os.path.exists(csv_path):
        print(f"  (skipping compute-time plot -- {csv_path} missing)")
        return
    df = pd.read_csv(csv_path)
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    for col, label, marker in [("lfc_us_per_node", "LFC (naive)", "o"),
                               ("mnp_e_us_per_node", "MNP-e", "s")]:
        ax.plot(df["n"], df[col], marker=marker, linewidth=2, label=label)
    ax.set_xlabel("Topology size |V|")
    ax.set_ylabel(r"Per-node compute time ($\mu$s)")
    ax.set_title("Per-node compute time: LFC vs. MNP-e")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = os.path.join(out_dir, "compute_time.png")
    fig.savefig(out, dpi=200)
    plt.close(fig)
    print(f"  saved -> {out}")


def plot_bpp_vs_R(csv_path: str, out_dir: str) -> None:
    if not os.path.exists(csv_path):
        print(f"  (skipping BPP-vs-R plot -- {csv_path} missing)")
        return
    df = pd.read_csv(csv_path)
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    for topo in df["topology"].unique():
        sub = df[df["topology"] == topo]
        ax.plot(sub["R"], sub["backup_links"], marker="o", linewidth=2, label=topo)
    ax.set_xlabel("Network availability requirement R")
    ax.set_ylabel("# Backup links needed")
    ax.set_title("HLP: # of BPP links to meet A(G) >= R")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = os.path.join(out_dir, "bpp_vs_R.png")
    fig.savefig(out, dpi=200)
    plt.close(fig)
    print(f"  saved -> {out}")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", default=os.path.join(ROOT, "results"))
    ap.add_argument("--plots-dir", default=os.path.join(ROOT, "plots"))
    args = ap.parse_args(argv)

    sweep_csv = os.path.join(args.results_dir, "all_topologies_summary.csv")
    if not os.path.exists(sweep_csv):
        sweep_csv = os.path.join(args.results_dir, "all_topologies.csv")

    if os.path.exists(sweep_csv):
        print(f"Loading data from {sweep_csv}...")
        df = pd.read_csv(sweep_csv)
        plot_traffic_avail(df, args.plots_dir)
        plot_topo_avail(df, args.plots_dir)
    else:
        print(f"  (no sweep CSV found in {args.results_dir})")
    plot_compute_time(os.path.join(args.results_dir, "compute_time.csv"), args.plots_dir)
    plot_bpp_vs_R(os.path.join(args.results_dir, "bpp_vs_availability.csv"), args.plots_dir)


if __name__ == "__main__":
    main()
