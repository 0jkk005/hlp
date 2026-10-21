# Hybrid Link Protection (HLP) -- research prototype

Implementation and evaluation of:

1. **HLP** (Hybrid Link Protection) by Geng *et al.*,
   *A Hybrid Link Protection Scheme for Ensuring Network Service
   Availability in Link-State Routing Networks*, J. Commun. Netw.
   22(1), Feb 2020, IEEE 9042897. ([base paper])

2. **TA-HLP** -- *Traffic-Adaptive Hybrid Link Protection* -- our
   extension that augments the BPP greedy selection with a
   traffic-weighted marginal-gain criterion, prioritising the
   protection of links that carry the heaviest traffic under a
   strict backup-link budget.

---

## Research status — results require regeneration

**This is a research prototype, not a validated publication artifact.** The
committed `results/` and `plots/` were generated before the corrections
tracked in [`docs/CORRECTIONS_CHECKLIST.md`](docs/CORRECTIONS_CHECKLIST.md).
Do not present them as results of the corrected method. The base-paper PDF was supplied for review but is not checked in; its analysis
is at [`docs/BASE_PAPER_COMPARISON.md`](docs/BASE_PAPER_COMPARISON.md). A manuscript
is not in this checkout. The four SNDlib JSON files contain
OD *demand instances*; their provenance and units must be independently
audited before using stronger labels such as measured NetFlow traces.
Failure probabilities are randomized, and SNDlib capacities are calibrated
from baseline demand at a configurable headroom factor, not observed links.

A corrected-code **end-to-end SNDlib simulation** was run separately; see
[`results/corrected_sndlib/README.md`](results/corrected_sndlib/README.md).
With four topologies, four budgets, five simulation seeds, and 500 sampled
failures per cell, **0/32** paired comparisons survived Bonferroni adjustment;
28/32 topology/budget/metric cells had at least one underperforming replicate.
This is an exploratory pipeline run, **not** an independently validated paper
result, a faithful Geng-et-al. comparison, or deployment testing.

The *older, pre-correction* SNDlib campaign had 32 statistical comparisons and **one**
Bonferroni-positive cell: Germany50 B=8, traffic-delivery fraction 0.9926241
(HLP) vs 0.9933258 (TA-HLP), corrected p=0.04691. The CSVs also contain
negative differences, including Abilene B=4: 0.970303 vs 0.945894
(topological conditional failure coverage) and 24/32 cells with at least
one TA-HLP replicate below HLP. There is **no** "never underperforms" claim.
The simulator imposes one failed edge per trial; its reported availability
is **conditional failure recovery coverage**, not steady-state availability.
Capacity penalties are still heuristic proxies, not congestion guarantees.

## Folder layout

```
hybrid-link-protection/
├── data/
│   ├── gml/                    # Internet Topology Zoo GML files
│   └── sndlib/                 # SNDlib network-design instances and OD demands
│       ├── abilene.json, geant.json, germany50.json, nobel-eu.json
├── src/                        # Implementation
│   ├── topology.py             #   Load/generate G; edges carry cost, prob_fail, capacity
│   ├── shortest_path.py        #   Dijkstra + path reconstruction
│   ├── lfc.py                  #   Naive Loop-Free Criterion (paper Section IV.A)
│   ├── mnp_e.py                #   MNP-e (Algorithm 2)
│   ├── tbfh.py                 #   TBFH baseline (paper Table 1; 2 SPTs/node)
│   ├── dmpa_e.py               #   DMPA-e baseline (paper Ref. [25])
│   ├── rocketfuel.py           #   Load Rocketfuel ISP topologies (.cch/.edgelist or synthetic BA)
│   ├── sndlib.py               #   Load SNDlib topology and OD demand instances
│   ├── path_construction.py    #   Forwarding paths from next-hop sets
│   ├── traffic_matrix.py       #   Gravity-model T(s,d) and matrix utilities
│   ├── availability.py         #   A(s,d), A(G), T_A(G)
│   ├── bpp.py                  #   BPP-inspired, not paper Algorithm 3
│   ├── ta_bpp.py               #   *** C-TA-BPP (Capacity-Constrained Traffic-Adaptive) ***
│   ├── protection.py           #   Compose LFC / HLP / C-TA-HLP
│   ├── simulator.py            #   Monte-Carlo datapath simulator with dynamic capacity enforcement
│   ├── metrics.py              #   Overhead, path stretch, expected coverage
│   └── utils.py                #   Logging, edge normalization helpers
├── experiments/                # CLI entry-points
│   ├── run_demo.py             #   Quick 1-topology 1-budget demo
│   ├── run_budget_sweep.py     #   Sweep B in {2..16}, produces CSV
│   ├── run_compute_time.py     #   Reproduce compute-time figures
│   ├── run_table_reproduction.py # Generate historical six-proxy comparison tables
│   └── run_statistical_experiments.py # Canonical statistical evaluation & ablation suite
├── plotting/
│   ├── plot_results.py         #   Budget-sweep + compute-time plots
│   └── plot_table_reproduction.py # Bar charts for Tables 3 & 4
├── results/                    # Unified experimental outputs
│   ├── sndlib/                 #   Historical SNDlib experiment outputs (pre-correction)
│   ├── all_topologies.csv      #   Base paper budget sweeps
│   ├── table3_compute_time.csv #   Historical Table 3 proxy
│   ├── table4_availability.csv #   Historical Table 4 proxy
│   └── plot_*.png              #   Benchmark evaluation curves
├── notebooks/                  # Self-contained Kaggle / Colab benchmark suites
│   └── C_TA_HLP_Kaggle_Benchmark.ipynb # Complete single-run cloud replication suite
├── tests/                      # Pytest unit & regression test suite
├── main.py                     # Convenience entry-point (supports --complete-run)
├── requirements.txt            # Version-ranged package dependencies
└── README.md
```

---

## Running on Kaggle / Google Colab

An unexecuted, self-contained notebook (not yet validated against the package) [`notebooks/C_TA_HLP_Kaggle_Benchmark.ipynb`](notebooks/C_TA_HLP_Kaggle_Benchmark.ipynb) is provided for cloud execution:
1. Open [Kaggle Notebooks](https://www.kaggle.com/code) $\rightarrow$ **New Notebook**.
2. Go to **File** $\rightarrow$ **Import Notebook** and upload `notebooks/C_TA_HLP_Kaggle_Benchmark.ipynb`.
3. Verify settings: Accelerator set to **None (CPU)** (provides 4 high-speed CPU cores and ~30 GB RAM).
4. Run interactively or click **Save Version** $\rightarrow$ **Save & Run All (Commit)** for background execution. All plots and CSVs are packaged into a `.zip` in the output panel.

---

## Installation

```bash
python -m pip install -r requirements.txt
```

## Topologies

### Internet Topology Zoo (GML)
Drop GML files from the [Internet Topology Zoo] under `data/gml/`.
A missing named topology now raises FileNotFoundError by default. Add
`--allow-synthetic` for a **labeled** BA sensitivity run; never confuse its
output with the named input.

For the original budget-sweep figure you will want at least:
- `Abilene.gml`     (11 nodes, 14 edges)
- `Geant2012.gml`   (~22 nodes, ~36 edges)
- `Sprint.gml`      (11 nodes, 18 edges)  -- **NOT the 315-node Sprint**

### Rocketfuel ISP Topologies (Full Evaluation)
The optional Rocketfuel evaluation requests four ISP topology labels from the base paper (Geng et al. 2020, Table 3):
- **Exodus**   — 79 nodes, 147 edges
- **Telstra**  — 108 nodes, 153 edges  
- **Tiscali**  — 161 nodes, 328 edges
- **Sprint315** — 315 nodes, 972 edges

**Important:** Real Rocketfuel `.cch`/`.edgelist` files from CAIDA are **not included** (download from https://www.caida.org/projects/ark/rocketfuel/). The pipeline **fails closed** unless `--allow-synthetic` is supplied; with that explicit switch it creates size-matched BA graphs, which are not Rocketfuel reproductions. The synthetic graphs preserve the *scale* and *degree distribution* but not the exact inferred ISP map structure. For an exact structural reproduction, place the Rocketfuel files in `data/rocketfuel/`.

---

## Quick start

```bash
# 0. Prototype multi-experiment suite (results require audit) (SNDlib + Tables 3 & 4 + Sweeps + Plots)
python main.py --complete-run  # fails if a named Rocketfuel input is missing

# 1. Demo on a synthetic topology
python main.py

# 2. Demo on a real topology
python main.py --topology data/gml/Abilene.gml --budget 8

# 3. Full budget sweep across all configured topologies + plot (original)
python main.py --sweep --plot --trials 300 --replicates 20

# 4. Compute-time experiment (synthetic BA graphs)
python -m experiments.run_compute_time

# 5. Generate plots only from existing CSVs
python -m plotting.plot_results

# 6. Full statistical evaluation suite (synthetic size-matched Rocketfuel topologies)
#    Includes: 5+ replicates, paired t-tests, Bonferroni correction, effect sizes,
#    ablation studies, diagnostic checks for underperformance, environment metadata
python -m experiments.run_statistical_experiments --topo-type rocketfuel \
    --budgets 2 4 6 8 10 12 14 16 --trials 100 --replicates 5 --seed 42 --allow-synthetic

# 7. Run six-proxy comparison tables (not paper reproduction)
python -m experiments.run_table_reproduction --repeat 5 --trials 300 --allow-synthetic
```

---

## CLI reference

### `main.py`
- `--complete-run`    Run the prototype benchmark suite in a single unified run.
- `--topology PATH`   GML file for the quick demo.
- `--sweep`           Run the full budget sweep across `--topologies`.
- `--topologies ...`  GML file names searched in `data/gml/`.
- `--budgets ...`     Backup-link budget list, default `2 4 6 8 10 12 14 16`.
- `--trials N`        Monte-Carlo failure trials per cell.
- `--replicates N`    Independent topology/traffic/failure repetitions.
- `--plot`            Generate plots after the sweep.
- `--allow-synthetic` Explicitly permit labeled BA substitutes for missing named inputs.

### `experiments/run_demo.py`
- Same as above for the demo path.

### `experiments/run_budget_sweep.py`
- Produces `results/all_topologies.csv`
- and one `results/budget_sweep_<topo>.csv` per topology.

### `experiments/run_compute_time.py`
- `--sizes 20 50 100 200` and `--degrees 3 5 8 10` sweep synthetic graphs.
- Produces `results/compute_time.csv` and `results/bpp_vs_availability.csv`.

---

## CSV output schema

`results/all_topologies_raw.csv` contains one row per method, budget,
topology, and replicate, including `node_count` and `edge_count`.
`results/all_topologies.csv` contains grouped means, standard
deviations, and 95% confidence-interval margins:

| column | meaning |
|---|---|
| topology | topology name |
| budget | B (max BPP links) |
| method | one of `LFC Only`, `HLP (Original)`, `TA-HLP (Proposed)` |
| node_count, edge_count | loaded topology size |
| `<metric>_mean` | replicate mean for a metric |
| `<metric>_std`, `<metric>_count` | sample standard deviation and replicate count |
| `<metric>_ci95` | approximate 95% confidence-interval margin |
| num_trials | Monte Carlo trials per replicate |

The aggregate file uses suffixed metric names such as
`traffic_availability_mean`; plotting supports both raw and aggregate
schemas. Confidence intervals are not informative when `replicates=1`.

---

## Historical proxy tables (not base-paper reproduction)

The codebase includes **six named algorithm proxies**. MNP-e is implemented
as LFC-equivalent repeated Dijkstra; MNP, TBFH, and DMPA-e are not
faithfully reproduced reference algorithms. The following historical
outputs are **not** a quantitative reproduction of the base paper:

| Method | Module | Paper reference |
|---|---|---|
| OSPF (single SPT, no backup next-hops) | `experiments/run_table_reproduction.py::compute_ospf` | baseline |
| LFC (one SPT per neighbour) | `src/lfc.py` | paper Section IV.A; Algorithm 1 is MNP |
| TBFH (2 SPTs per node, downstream criterion) | `src/tbfh.py` | paper Ref. [17] |
| MNP (tree-only contribution check) | `experiments/run_table_reproduction.py::compute_mnp` | paper Ref. [36] |
| DMPA-e (hop-count aware LFC) | `src/dmpa_e.py` | paper Ref. [25] |
| MNP-e output proxy (not paper Algorithm 2 code) | `src/mnp_e.py` | coverage-equivalent only |

Run the historical proxies for **Table 3** (per-node compute time) and **Table 4** (network availability) across Abilene + all 4 Rocketfuel ISP topologies:

```bash
# Tables 3 and 4 (defaults to Abilene + Exodus + Telstra + Tiscali + Sprint315)
python -m experiments.run_table_reproduction --repeat 5 --trials 300 --allow-synthetic

# Or just Table 3 (compute time)
python -m experiments.run_table_reproduction --only table3

# Or just Table 4 (availability)
python -m experiments.run_table_reproduction --only table4 --trials 300
```

Output CSVs:

- `results/table3_compute_time.csv` -- columns: `topology, |V|, |E|, OSPF, LFC, TBFH, MNP, DMPA-e, MNP-e` (values in µs)
- `results/table4_availability.csv` -- columns: `topology, |V|, |E|, OSPF, LFC, TBFH, MNP, DMPA-e, MNP-e` (values in %)

Bar charts:

```bash
python -m plotting.plot_table_reproduction
```
produces `plots/table3_compute_time_bars.png` (log y-axis) and `plots/table4_availability_bars.png`.

### Rocketfuel topologies

The proxy experiment requests the four Rocketfuel topologies used by the base paper
(Exodus, Telstra, Tiscali, Sprint 315-node) via `src/rocketfuel.py`. If the
data files are absent the loader falls back to a **synthetic BA graph**
matching the paper's exact `|V|, |E|` counts (`79/147, 108/153, 161/328, 315/972`)
when explicitly requested with `--allow-synthetic`. For an exact structural study, obtain the Rocketfuel dataset
from CAIDA (https://www.caida.org/projects/ark/rocketfuel/) and drop the files
as `data/rocketfuel/<NAME>.cch` or `data/rocketfuel/<NAME>.edgelist`. The historical proxy results do **not** establish quantitative reproduction
of either table. In particular, the current implementation of MNP-e is
LFC-equivalent and the DMPA-e/TBFH/MNP implementations are approximations.


### Adding TBFH and DMPA-e to the budget sweep

Main TA-HLP evaluation can optionally include these as additional no-BPP baselines:

```bash
python main.py --sweep --topologies Abilene.gml Geant2012.gml Sprint.gml \
               --budgets 2 4 6 8 10 12 14 16 --trials 300 --plot \
               --include-extended-baselines
```

The plots then display all 5 methods (LFC-Only, TBFH, DMPA-e, HLP-Original, TA-HLP).

---

## Reproduction Workflow Summary

1. Place GML files under `data/gml/`.
2. Run full sweep: `python main.py --sweep --plot --trials 300 --replicates 20`.
3. Generated PNGs land in `plots/`:
   - `traffic_avail_vs_budget_<TOPO>.png` -- main paper figure
   - `topo_avail_vs_budget_<TOPO>.png`    -- topological availability
   - `compute_time.png`                   -- LFC vs MNP-e timing
   - `bpp_vs_R.png`                       -- BPP links vs. R threshold

### 🚀 **To Run Full Statistical & Ablation Experiments**

```bash
# Full statistical evaluation (synthetic Rocketfuel topologies)
python -m experiments.run_statistical_experiments --topo-type rocketfuel \
    --budgets 2 4 6 8 10 12 14 16 --trials 100 --replicates 5 --seed 42 --allow-synthetic

# With ablation studies
python -m experiments.run_statistical_experiments --topo-type rocketfuel \
    --budgets 2 4 6 8 10 12 14 16 --trials 100 --replicates 5 --seed 42 --run-ablation --allow-synthetic
```

---

## Algorithmic notes

- **MNP-e proxy:** `src/mnp_e.py` uses one ordinary Dijkstra per neighbor,
  exactly the LFC feasibility test. It does **not** implement the paper's
  incremental SPF or negative-edge modification; no MNP-e timing improvement
  should be claimed for this implementation.

- **`A(s,d)` versus Inclusion-Exclusion.** The paper's exact
  Inclusion-Exclusion over all paths is exponential. We use the same
  single-path approximation the existing scaffolding used:
  `A(s,d) = product of (1 - r_e)` along the single shortest path.
  An exact `availability.exact_end_to_end_availability` is provided
  for sanity-check on tiny graphs.

- **BPP gain is a proxy:** `src/bpp.py` evaluates a local repair from the
  detecting router while retaining the traversed prefix, but its reliability
  product and `p_e` factor are not an exact exclusive-failure marginal or
  proved base-paper Equation 6. The objective and simulator still need
  per-failure flow-conserving reconciliation (checklist P0).

- **Traffic Matrix** is a degree-based gravity model with optional
  jitter. Plug in a real matrix by replacing `traffic_matrix.py`.

---

## Author & Maintainer

- **Md. Iqbal Haider Khan**
  - GitHub: [@ihkokil](https://github.com/ihkokil)
  - Email: [ihkokil@gmail.com](mailto:ihkokil@gmail.com)

---

## Citing

HLP base paper:
```bibtex
@article{geng2020hlp,
  title={A Hybrid Link Protection Scheme for Ensuring Network Service Availability in Link-state Routing Networks},
  author={Geng, Haijun and Zhang, Han and Shi, Xingang and Wang, Zhiliang and Yin, Xia and Zhang, Ju and Hu, Zhiguo and Wu, Yong},
  journal={Journal of Communications and Networks},
  volume={22},
  number={1},
  pages={46--60},
  year={2020},
  doi={10.1109/JCN.2019.000056}
}
```

[base paper]: https://ieeexplore.ieee.org/document/9042897
[Internet Topology Zoo]: http://www.topology-zoo.org/
