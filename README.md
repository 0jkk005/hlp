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

## 🔬 Full Statistical Evaluation Summary

**Key findings from empirical and statistical evaluation:**

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Reproducible implementation | ✅ | 5+ replicates, fixed seeds, environment metadata |
| Statistical rigor | ✅ | Paired one-sided t-tests, Bonferroni correction, Cohen's d, 95% CIs |
| Real Rocketfuel topologies | ❌ | Synthetic BA graphs matching (|V|,|E|) only |
| Statistically significant advantage | ❌ | 0/16 comparisons significant after Bonferroni |
| "Never underperforms" claim | ❌ | FALSE — TA-HLP < HLP in ~50% of cells |
| Effect size | ⚠️ | Small (avg Δ = 0.01%), inconsistent direction |

**Conclusion:** TA-HLP is a **sound algorithmic contribution** with a rigorous evaluation pipeline, but the empirical evidence on synthetic size-matched topologies does **not** support a claim of superiority over HLP. The paper should be framed as a methodological contribution with inconclusive empirical validation.

Detailed evaluation logs, statistical comparison outputs, and environment metadata are stored under `results/`.

---

## Folder layout

```
hybrid-link-protection/
├── data/gml/                  # Internet Topology Zoo GML files (you supply them)
├── src/                       # implementation
│   ├── topology.py            #   load/generate G; edges carry cost, prob_fail, capacity
│   ├── shortest_path.py       #   Dijkstra + path reconstruction
│   ├── lfc.py                  #   naive Loop-Free Criterion (Algorithm 1, baseline)
│   ├── mnp_e.py                #   MNP-e (Algorithm 2)
│   ├── tbfh.py                 #   TBFH baseline (paper Table 1; 2 SPTs/node)
│   ├── dmpa_e.py               #   DMPA-e baseline (paper Ref. [25])
│   ├── rocketfuel.py           #   load Rocketfuel ISP topologies (.cch/.edgelist)
│   ├── path_construction.py   #   forwarding paths from next-hop sets
│   ├── traffic_matrix.py       #   gravity-model T(s,d)
│   ├── availability.py         #   A(s,d), A(G), T_A(G)
│   ├── bpp.py                  #   Backup Path Protection (Algorithm 3)
│   ├── ta_bpp.py               #   *** TA-BPP (our contribution) ***
│   ├── protection.py           #   compose LFC / HLP / TA-HLP
│   ├── simulator.py            #   Monte-Carlo single-link failures
│   ├── metrics.py              #   overhead, path stretch, expected coverage
│   └── utils.py                #   logging, helpers
├── experiments/               # CLI entry-points
│   ├── run_demo.py             #   quick 1-topology 1-budget demo
│   ├── run_budget_sweep.py     #   sweep B in {2..16}, produces CSV
│   ├── run_compute_time.py     #   reproduce paper Figs. 8-10, 13-15
│   ├── run_table_reproduction.py # reproduce paper Tables 3 & 4 (all 6 methods)
│   └── run_statistical_experiments.py # full statistical evaluation & ablation suite
├── plotting/
│   ├── plot_results.py        #   budget-sweep + compute-time plots
│   └── plot_table_reproduction.py # bar charts for Tables 3 & 4
├── results/                    # CSV outputs (auto-created)
├── plots/                      # PNG outputs (auto-created)
├── main.py                     #   convenience entry-point
├── requirements.txt
└── README.md
```

---

## Installation

```bash
python -m pip install -r requirements.txt
```

## Topologies

### Internet Topology Zoo (GML)
Drop GML files from the [Internet Topology Zoo] under `data/gml/`.
The code recovers automatically if a file is missing -- it falls
back to a 30-node Barabási–Albert graph and logs a warning.

For the original budget-sweep figure you will want at least:
- `Abilene.gml`     (11 nodes, 14 edges)
- `Geant2012.gml`   (~22 nodes, ~36 edges)
- `Sprint.gml`      (11 nodes, 18 edges)  -- **NOT the 315-node Sprint**

### Rocketfuel ISP Topologies (Full Evaluation)
The full evaluation uses the four Rocketfuel ISP topologies from the base paper (Geng et al. 2020, Table 3):
- **Exodus**   — 79 nodes, 147 edges
- **Telstra**  — 108 nodes, 153 edges  
- **Tiscali**  — 161 nodes, 328 edges
- **Sprint315** — 315 nodes, 972 edges

**Important:** Real Rocketfuel `.cch`/`.edgelist` files from CAIDA are **not included** (download from https://www.caida.org/projects/ark/rocketfuel/). The pipeline falls back to **synthetic Barabási–Albert graphs** matching the exact (|V|,|E|) counts and logs a warning. The synthetic graphs preserve the *scale* and *degree distribution* but not the exact inferred ISP map structure. For an exact structural reproduction, place the Rocketfuel files in `data/rocketfuel/`.

---

## Quick start

```bash
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
#    ablation studies, "never underperforms" verification, environment metadata
python -m experiments.run_statistical_experiments --topo-type rocketfuel \
    --budgets 2 4 6 8 10 12 14 16 --trials 100 --replicates 5 --seed 42

# 7. Reproduce base paper Tables 3 & 4 (all 6 methods)
python -m experiments.run_table_reproduction --repeat 5 --trials 300
```

---

## CLI reference

### `main.py`
- `--topology PATH`   GML file for the quick demo.
- `--sweep`           Run the full budget sweep across `--topologies`.
- `--topologies ...`  GML file names searched in `data/gml/`.
- `--budgets ...`     Backup-link budget list, default `2 4 6 8 10 12 14 16`.
- `--trials N`        Monte-Carlo failure trials per cell.
- `--replicates N`    Independent topology/traffic/failure repetitions.
- `--plot`            Generate plots after the sweep.

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

## Reproducing the base paper (Tables 3 and 4)

The codebase ships with **all six methods** evaluated in the base paper:

| Method | Module | Paper reference |
|---|---|---|
| OSPF (single SPT, no backup next-hops) | `experiments/run_table_reproduction.py::compute_ospf` | baseline |
| LFC (one SPT per neighbour) | `src/lfc.py` | Algorithm 1 |
| TBFH (2 SPTs per node, downstream criterion) | `src/tbfh.py` | paper Ref. [17] |
| MNP (tree-only contribution check) | `experiments/run_table_reproduction.py::compute_mnp` | paper Ref. [36] |
| DMPA-e (hop-count aware LFC) | `src/dmpa_e.py` | paper Ref. [25] |
| MNP-e (paper Algorithm 2) | `src/mnp_e.py` | Algorithm 2 |

Run the reproductions of **Table 3** (per-node compute time) and **Table 4** (network availability) across Abilene + all 4 Rocketfuel ISP topologies:

```bash
# Tables 3 and 4 (defaults to Abilene + Exodus + Telstra + Tiscali + Sprint315)
python -m experiments.run_table_reproduction --repeat 5 --trials 300

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

The reproduction loads the four Rocketfuel topologies used by the base paper
(Exodus, Telstra, Tiscali, Sprint 315-node) via `src/rocketfuel.py`. If the
data files are absent the loader falls back to a **synthetic BA graph**
matching the paper's exact `|V|, |E|` counts (`79/147, 108/153, 161/328, 315/972`)
and logs a warning. For an exact reproduction, download the Rocketfuel dataset
from CAIDA (https://www.caida.org/projects/ark/rocketfuel/) and drop the files
as `data/rocketfuel/<NAME>.cch` or `data/rocketfuel/<NAME>.edgelist`. We
verified that the synthetic fallback reproduces the **qualitative ordering** of
both tables: LFC ≫ MNP-e ≈ MNP ≈ DMPA-e > TBFH > OSPF on compute time, and
OSPF < TBFH < MNP < DMPA-e ≤ MNP-e = LFC on availability — exactly the order
the paper reports in Tables 3 and 4.

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
    --budgets 2 4 6 8 10 12 14 16 --trials 100 --replicates 5 --seed 42

# With ablation studies
python -m experiments.run_statistical_experiments --topo-type rocketfuel \
    --budgets 2 4 6 8 10 12 14 16 --trials 100 --replicates 5 --seed 42 --run-ablation
```

---

## Algorithmic notes

- **MNP-e** is implemented using Theorems 5-6 from the paper: for each
  neighbour `x` of `c`, we modify the weight of `(c,x)` to `-L(c,x)`
  and run Dijkstra. The paper's claim that MNP-e costs *less* than
  Dijkstra is achieved only with a real i-SPF primitive, which
  NetworkX doesn't provide. We therefore keep the asymptotic cost at
  `O(deg(c) * |E| lg |V|)`, identical to LFC's *worst-case*, but with
  a smaller constant (no complete SPT recomputation per neighbour).
  See `src/mnp_e.py` docstring. This is an *implementation assumption*,
  not a paper claim.

- **`A(s,d)` versus Inclusion-Exclusion.** The paper's exact
  Inclusion-Exclusion over all paths is exponential. We use the same
  single-path approximation the existing scaffolding used:
  `A(s,d) = product of (1 - r_e)` along the single shortest path.
  An exact `availability.exact_end_to_end_availability` is provided
  for sanity-check on tiny graphs.

- **`A*(s,d)` in BPP** is computed as the availability of the single
  new shortest path in `G \ e`, again per the paper's approximation
  when explicit path enumeration is intractable.

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
