# Publication correction checklist

Status: [x] implemented in this branch; [ ] outstanding. This is a work plan, not a claim that the current CSVs have been validated. **Do not use existing plots or CSVs as evidence for the revised implementation** until the full campaign has been rerun and audited. The foundational paper was supplied as a conversation attachment and audited in `docs/BASE_PAPER_COMPARISON.md`; it is not committed. No manuscript has been supplied. Add only source copies you have rights to redistribute.

## P0 — validity blockers

- [x] Make BPP and traffic-aware candidate path scoring use a detour from the *failure-detecting router*, retaining the original prefix, not a new source-to-destination path. Add a counterexample test.
- [ ] Replace the capacity score with a scenario-consistent, flow-specific marginal *delivered demand* calculation; account for surviving unaffected and LFA flows; never sum simultaneous loads from mutually exclusive failed-edge scenarios. Compare to exact per-edge scenario enumeration on small graphs.
- [ ] Establish provenance of every SNDlib JSON (primary instance URL/version, units, original demand origin, license and SHA256); provide a documented preparation/verification script. Do not call these NetFlow unless the source establishes that fact.
- [x] Flag historical dominance, congestion, NetFlow and paper-reproduction claims as unverified in the README and package docs; report contrary results with absolute differences.
- [ ] Replace or remove unsupported statements embedded in the independent notebook implementation before presenting it as an executable research artifact.
- [x] Read the user-supplied 15-page base paper and document its actual equations, algorithms, tables, and code mismatches in `docs/BASE_PAPER_COMPARISON.md`.
- [ ] Supply the manuscript for line-by-line comparison; decide how readers should access the base paper without imposing its CC BY-NC terms on this codebase.
- [x] Execute a separate exploratory end-to-end SNDlib campaign with the initially corrected code (4 topologies × 4 budgets × 5 seeds × 500 trials); see `results/corrected_sndlib/README.md`. No adjusted comparison was significant.
- [ ] Recompute and audit **every** result/plot after the capacity objective, faithful comparator and data provenance have been repaired; keep historical results labeled as such.

## P1 — experimental validity

- [ ] Define conditional single-failure restoration coverage separately from unconditional steady-state availability, probability of failure, delivered-demand fraction, and packet loss; implement and test estimators for each claimed quantity.
- [ ] Document failure units/time horizon and justify probabilities; evaluate uniform and hazard-weighted *exclusive* failures and correlated/shared-risk failures separately.
- [ ] Replace or relabel MNP-e, TBFH, DMPA-e and MNP baseline proxies. Do not call proxy timing/results a reproduction of the base paper. See `docs/BASE_PAPER_COMPARISON.md` pp. 54–58.
- [ ] Add a *separate* faithful Geng et al. Algorithm 3 baseline using only `(v,d)` detector-origin pairs in `e.P` and the paper's Eq. 6/availability semantics; do not silently change the extended all-upstream-flow baseline.
- [ ] Reconcile the paper's apparently inconsistent use of `r(u,v)` as a failure probability in Section III.A and a working-path multiplier in Eq. 1; state unambiguous conventions for our own experiments.
- [ ] Validate primary and alternate hop-by-hop forwarding and ECMP/tie handling against reference traces; try all feasible alternates or specify a deterministic router policy.
- [ ] Test time-ordered OD snapshots: optimize using past data, evaluate on future demands, report stale/perturbed-demand sensitivity and proper uncertainty.
- [x] Pair HLP and TA-HLP on explicit replicate IDs; reject duplicate/unpaired cells. Keep traffic-variant ablations in separate result families.
- [ ] Pair at failure-scenario and time-snapshot level, predefine the hypothesis/comparison family before new experiments, and report two-sided sensitivity and independent uncertainty.
- [ ] Add equal-budget random, HLP, demand-only, capacity-only, probability-only and exact/MILP small-instance comparators; hold inputs, failure draws, environment and budget equal.
- [ ] Evaluate real capacities or explicitly label baseline-load-calibrated capacities as synthetic engineering scenarios; vary headroom and overloaded-baseline cases.
- [ ] Evaluate per-failed-link lost demand, utilization, route stretch, bridges, topology sensitivity, prediction error, policy memory, time and peak RAM.

## P2 — artifact and deployment

- [x] Fail closed on missing named GML/Rocketfuel benchmark inputs unless an explicit synthetic fallback is requested; label synthetic data with synthetic provenance.
- [ ] Lock direct and transitive dependency versions or containerize; add `python -m pytest` and a small smoke campaign to CI.
- [ ] Save exact command/config, Git SHA, versions, input hashes, selected links, failures and full raw outcome data for every published table.
- [ ] Remove duplicate notebook implementation or import the tested package; execute and save an output-validated notebook with versions and dataset provenance.
- [ ] Replace SID-depth and TCAM-entry proxy formulas with correctly encoded, measured forwarding policies or explicitly downgrade them to illustrative quantities.
- [ ] Add tests for disconnected graphs, zero demand, zero/invalid budgets, negative/nonfinite capacity and failures, equal-cost paths, loops, and reproducibility across processes.
- [ ] Benchmark whole-algorithm asymptotic scaling and memory, not just SPT per-node time; report hardware, confidence intervals and failure-to-complete thresholds.
- [ ] Add manuscript sections: threat/system model, mathematical objective and complexity, related-work comparison, experimental protocol, ablation, negative results, limitations, ethics/data/code availability.
- [ ] Perform independent artifact replication; release tagged, archived source/results with a DOI after all manuscript tables match regenerated outputs.

## Reproduction guardrails

- The existing `results/` and `plots/` predate the code fixes here and must not be interpreted as results of the corrected method.
- `README.md` is an implementation guide, not an independently checked base-paper source.
- SNDlib demand instances are network-design inputs until provenance establishes anything more specific; randomized failure probabilities and demand-calibrated capacities are simulation assumptions.
- No IDS/ML model is present: classifier accuracy, F1/ROC, model weights and train/test scaler leakage are not applicable to this work.
