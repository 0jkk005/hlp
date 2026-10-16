"""Plots for the Table 3 / Table 4 base-paper reproductions.

Produces:
    plots/table3_compute_time_bars.png   (per-method bar chart per topology, log y-axis)
    plots/table4_availability_bars.png   (per-method availability, linear y-axis)
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

METHOD_ORDER = ["OSPF", "LFC", "TBFH", "MNP", "DMPA-e", "MNP-e"]
METHOD_COLORS = {
    "OSPF": "tab:gray",
    "LFC": "tab:purple",
    "TBFH": "tab:green",
    "MNP": "tab:orange",
    "DMPA-e": "tab:brown",
    "MNP-e": "tab:blue",
}


def plot_table3(csv_path: str, out_dir: str) -> None:
    if not os.path.exists(csv_path):
        print(f"  (skipping Table 3 plot -- {csv_path} missing)")
        return
    df = pd.read_csv(csv_path)
    fig, ax = plt.subplots(figsize=(9.0, 4.5))
    x = range(len(df))
    width = 0.13
    for i, m in enumerate(METHOD_ORDER):
        if m not in df.columns:
            continue
        ax.bar([xi + (i - 2.5) * width for xi in x],
               df[m], width, label=m,
               color=METHOD_COLORS.get(m))
    ax.set_xticks(list(x))
    ax.set_xticklabels(df["topology"], rotation=15)
    ax.set_yscale("log")
    ax.set_ylabel("Per-node compute time (us, log scale)")
    ax.set_title("Table 3 reproduction: per-node compute time on real ISP topologies")
    ax.legend(ncol=6, loc="upper left", framealpha=0.7, fontsize=9)
    ax.grid(True, alpha=0.3, which="both")
    fig.tight_layout()
    out = os.path.join(out_dir, "table3_compute_time_bars.png")
    fig.savefig(out, dpi=200)
    plt.close(fig)
    print(f"  saved -> {out}")


def plot_table4(csv_path: str, out_dir: str) -> None:
    if not os.path.exists(csv_path):
        print(f"  (skipping Table 4 plot -- {csv_path} missing)")
        return
    df = pd.read_csv(csv_path)
    fig, ax = plt.subplots(figsize=(9.0, 4.5))
    x = range(len(df))
    width = 0.13
    for i, m in enumerate(METHOD_ORDER):
        if m not in df.columns:
            continue
        ax.bar([xi + (i - 2.5) * width for xi in x],
               df[m], width, label=m,
               color=METHOD_COLORS.get(m))
    ax.set_xticks(list(x))
    ax.set_xticklabels(df["topology"], rotation=15)
    ax.set_ylabel("Network availability (%)")
    ax.set_ylim(75, 100.5)
    ax.set_title("Table 4 reproduction: topological availability on real ISP topologies")
    ax.legend(ncol=6, loc="lower right", framealpha=0.7, fontsize=9)
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    out = os.path.join(out_dir, "table4_availability_bars.png")
    fig.savefig(out, dpi=200)
    plt.close(fig)
    print(f"  saved -> {out}")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", default=os.path.join(ROOT, "results"))
    ap.add_argument("--plots-dir", default=os.path.join(ROOT, "plots"))
    args = ap.parse_args(argv)
    ensure_dir(args.plots_dir)
    plot_table3(os.path.join(args.results_dir, "table3_compute_time.csv"), args.plots_dir)
    plot_table4(os.path.join(args.results_dir, "table4_availability.csv"), args.plots_dir)


if __name__ == "__main__":
    main()
