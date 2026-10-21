# Corrected-code SNDlib experiment — exploratory, NOT publication evidence

This output is an **actual end-to-end experiment**, distinct from unit tests. It was produced after the initial local-repair and scoring changes and does not replace the historical `results/sndlib/` output. Do not mix these two sets of CSVs or label either one a base-paper reproduction.

Command (run at repository root on 2026-10-21):

```bash
python -m experiments.run_statistical_experiments --topo-type sndlib \
  --budgets 2 4 6 8 --trials 500 --replicates 5 --seed 42 \
  --out results/corrected_sndlib
```

Environment and exact CLI are recorded in `environment_metadata.json`; full console output in `run.log`. This run took approximately 597 seconds in the development sandbox. `all_topologies_raw.csv` has 240 rows: 4 topology labels × 4 budgets × 5 seeds × 3 methods. The 500 trials per cell sample one failed link **conditional on a failure**; they are not steady-state annual availability. The same SNDlib OD demand instance is reused over seeds, not five independent measured traces. Capacities are demand-calibrated simulation assumptions; failure probabilities are synthetic. The baseline named `HLP (Original)` is a **modified proxy**, not Geng et al.'s Algorithm 2/3/Eq. 6 baseline.

## Measured findings in this run

- **0 of 32** one-sided comparisons pass the configured Bonferroni correction. Three traffic comparisons (Germany50, budgets 2, 6, 8) have uncorrected `p<0.05`; none have `p<0.01`.
- At Abilene B=2, traffic-delivery fraction is 0.812250 for the HLP proxy versus **0.806940** for TA-HLP (difference **−0.005309**). At Abilene B=4, the difference is **−0.004972**.
- At Germany50 B=8, traffic-delivery fraction is 0.992624 versus **0.993493** (difference **+0.000869**, adjusted `p=1.0`). A positive observed mean is not a multiplicity-corrected result.
- `never_underperforms.csv` records **28 of 32** topology/budget/metric cells where at least one sampled TA-HLP replicate is below HLP. No dominance claim is supported.
- These figures reflect *this code and this experiment*, not a validated improvement over the published paper. Because the congestion scoring proxy is still not scenario-consistent, do not submit these results as a final contribution.

## Reproduction and integrity

- `all_topologies_raw.csv` SHA256: `26f11149e00cc0e0747d965e6f47cd6476c7a0fcf054cf6b171b300a3a1016b2`
- `statistical_comparisons.csv` SHA256: `b91ebb327d848548eab9f8780552e9dd2ef1fc9d27cbb25b47d6fe9c48990504`

The command overwrites this directory's generated files if rerun. It does not overwrite `results/sndlib/`. For outstanding scientific requirements see `docs/CORRECTIONS_CHECKLIST.md` and `docs/BASE_PAPER_COMPARISON.md`.
