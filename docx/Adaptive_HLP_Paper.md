# Adaptive Hybrid Link Protection (TA-HLP) for Failure-Resilient Link-State Routing Networks

## Abstract
Link-state routing protocols such as OSPF and IS-IS are heavily relied upon in large-scale IP networks. While standard shortest-path routing handles topology changes, the convergence delay during a failure causes transient loops and unacceptable packet loss. The Hybrid Link Protection (HLP) scheme was proposed to guarantee service availability by combining Loop-Free Criterion (LFC) with a Maximum Not Protected edges (MNP-e) selection and a Backup Path Protection (BPP) algorithm. However, Original HLP is purely topological—it does not use the traffic volume carried by each link. In this paper, we propose **Traffic-Adaptive Hybrid Link Protection (TA-HLP)**, an extension that integrates a gravity-based traffic matrix into the BPP stage. We test whether traffic-aware selection improves Traffic Availability under strict backup-link budgets; the benefit is expected to be topology- and workload-dependent rather than universal.

---

## 1. Introduction
Modern IP networks require ultra-high availability. When a link fails, standard IP routing can take hundreds of milliseconds to seconds to re-converge, during which micro-loops form and critical traffic is dropped. IP Fast Reroute (IP-FRR) mechanisms mitigate this by computing backup paths in advance. 

A recently proposed scheme, Hybrid Link Protection (HLP), achieves 100% topological availability by mathematically combining LFC (Loop-Free Criterion) with tunnel-based Backup Path Protection (BPP). While HLP minimizes the number of tunnels required (overhead), it is fundamentally oblivious to the underlying traffic matrix. In real networks, traffic is often skewed; a small fraction of core links may carry a large fraction of the data.

We hypothesize that an optimal protection scheme should be **traffic-aware**. In this paper, we extend HLP to **TA-HLP**, which prioritizes backup tunnels for links that contribute the most to the network's total traffic volume.

---

## 2. Background and Related Work
The baseline HLP algorithm operates in two stages:
1. **Stage 1 (MNP-e)**: Iteratively evaluates nodes and determines the Maximum Not Protected edges that cannot be protected purely via LFC.
2. **Stage 2 (BPP)**: To protect the remaining vulnerable edges, it computes backup paths (tunnels). It uses a greedy heuristic to pick a subset of backup links $E_{BPP} \subseteq E$ that maximizes the Topological Availability $A(G)$ until a threshold $R$ is reached.

The greedy choice in standard BPP is based on $\Delta A_{j,k}$, the marginal increase in *topological* availability if link $(j,k)$ is protected. It does not account for the bandwidth flowing over $(j,k)$.

---

## 3. Proposed Methodology: TA-HLP
We extend the standard HLP by introducing a Traffic Matrix $T$ where $T(s,d)$ is the traffic demand between source $s$ and destination $d$.

### 3.1 Gravity Model Traffic Matrix
In the absence of live flow data, we model the traffic using a degree-based gravity model, typical in networking research:
$$ T(s,d) = \frac{deg(s) \times deg(d)}{\sum_{k \in V} deg(k)} \times \text{scale} $$

### 3.2 Traffic-Aware BPP (TA-BPP)
During the BPP stage, instead of greedily selecting the backup link that maximizes Topological Availability $A(G)$, **TA-BPP** selects the link that maximizes the **Traffic Availability $T\_A(G)$**. 

The marginal gain for protecting a link $e$ is redefined as:
$$ \Delta T\_A(e) = \sum_{p \in P_{failed}(e)} Traffic(p) \times (1 - prob\_fail(e)) $$
Where $P_{failed}(e)$ is the set of all source-destination paths that were broken but are now successfully rerouted because link $e$ was added to the protected BPP set.

---

## 4. Experimental Setup
To rigorously evaluate TA-HLP, we developed a discrete-event simulator in Python.

**Topologies:** We evaluate three locally supplied GML topologies:
1. **Sprint** (US Backbone)
2. **Abilene** (Internet2)
3. **Geant2012** (European Research Network)

The loaded files must be reported with their exact node and edge counts. In the current artifact, Abilene is 11/14, Geant2012 is 40/61, and Sprint is 11/18 (nodes/edges). The latter two do not match the benchmark sizes used in the baseline comparison and must not be described as direct reproductions of those benchmark topologies without replacing the files or relabeling the experiments.

**Simulation Parameters:**
* **Failure Model**: Single-link failure model with link failure probabilities uniformly distributed in $[0.001, 0.02]$.
* **Trials**: 300 Monte Carlo failure injections per configuration and
  independent replicate seeds for confidence intervals.
* **Overhead Budget**: We constrain the maximum number of backup links the BPP algorithm is allowed to utilize. This forces the greedy algorithm to make difficult choices. We sweep this budget from 2 to 16 links.

---

## 5. Results and Evaluation

The core hypothesis is that under constrained overhead budgets, TA-HLP
can protect high-volume traffic, yielding a higher overall Traffic
Availability ratio than standard HLP. The claim is conditional: the
gain depends on traffic skew, topology, failure distribution, and budget.
Results must therefore be reported with replicate-level confidence
intervals rather than as a single-seed improvement.

### 5.1 Abilene Topology
With the current 11-node/14-edge file and one replicate, the regenerated
results at a budget of **4** are **89.96%** for LFC Only, **96.72%** for
Original HLP, and **96.72%** for TA-HLP. At a budget of **6**, the values
are **89.96%**, **97.71%**, and **97.71%**, respectively. These are
descriptive single-replicate estimates, not statistically supported
claims; the 95% replicate confidence interval is unavailable with
`n=1`.

### 5.2 Geant2012 Topology
For the current 40-node/61-edge file, at a budget of **4** the values are
**97.70%** for LFC Only, **98.79%** for Original HLP, and **98.84%** for
TA-HLP. At a budget of **6**, they are **97.70%**, **98.94%**, and
**99.04%**, respectively. The absolute gains over HLP are 0.05 and 0.10
percentage points in this single replicate.

### 5.3 Sprint Topology
For the current 11-node/18-edge file, at budgets of **4** and **6**,
HLP and TA-HLP are identical at **98.60%** and **99.28%**, respectively.
This result is not evidence about the 315-node/972-edge Sprint benchmark
used in the baseline paper.

### 5.4 Discussion
When resources (e.g., router memory for tunnel state) are strictly
constrained, network operators cannot protect every vulnerable link.
The experiment tests whether prioritizing links via a traffic matrix
improves service-level availability over topologically driven HLP; it
does not imply strict superiority for every topology or budget.

---

## 6. Conclusion
In this paper, we presented TA-HLP, a traffic-aware extension to the
Hybrid Link Protection algorithm. By integrating a gravity traffic
matrix into the greedy BPP selection phase, TA-HLP optimizes for the
traffic volume that survives a failure. The experiment quantifies when
TA-HLP improves traffic availability over standard HLP under strict
overhead budgets using raw replicate results and confidence intervals.
Absolute data-volume savings require calibrated traffic demands and are
not inferred from a normalized availability ratio alone.

### Future Work
The current simulator validates single-link recovery using an explicit
post-failure shortest repair path. It does not model tunnel capacity,
control-plane signaling delay, or correlated failures. Future work will
evaluate Shared Risk Link Group (SRLG) and multiple-failure scenarios,
capacity-aware repair, and dynamic time-series traffic matrices.
