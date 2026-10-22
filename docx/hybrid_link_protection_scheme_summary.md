# A Hybrid Link Protection Scheme for Ensuring Network Service Availability in Link-State Routing Networks

## Rewritten and Summarized Paper

**Authors:** Haijun Geng, Han Zhang, Xingang Shi, Zhiliang Wang, Xia
Yin, Ju Zhang, Zhiguo Hu, and Yong Wu\
**Published in:** *Journal of Communications and Networks*, Vol. 22,
No. 1, February 2020, pp. 46--60\
**DOI:**
[10.1109/JCN.2019.000056](https://doi.org/10.1109/JCN.2019.000056)

> **Scope note:** This Markdown document is a structured paraphrase and
> technical summary of the supplied paper, not a verbatim transcription.
> It preserves the paper's main concepts, algorithmic structure,
> equations, evaluation setup, and reported results. Some diagrams and
> long proofs are described in words rather than reproduced.

------------------------------------------------------------------------

## Abstract

Modern Internet services---including voice over IP (VoIP), video
streaming, and mission-critical applications---need high network
availability. Traditional link-state routing protocols such as OSPF and
IS-IS react to a link failure by distributing link-state updates and
recalculating routes. During convergence, traffic may be interrupted or
dropped.

Loop-Free Alternates (LFA), based on the Loop-Free Criterion (LFC),
allow a router to switch quickly to an alternate next hop. However, LFC
does not protect every possible single-link failure. Other approaches
can provide broader protection but may require substantial computation,
extra signaling, or changes to packet forwarding.

The paper proposes **Hybrid Link Protection (HLP)**, a two-stage
approach:

1.  **MNP-e (extended Multiple Next-hop Protection)** efficiently
    computes loop-free alternate next hops.
2.  **BPP (Backup Path Protection)** identifies the remaining
    unprotected links and selects a small set for multi-hop backup
    protection, based on each link's contribution to network
    availability.

The authors evaluate the method on real ISP topologies and synthetic
networks. They report that MNP-e offers LFC-level availability with low
computation overhead, while HLP reaches high availability using
substantially less computation than protecting every link with a
multi-hop backup path.

## 1. Problem and Motivation

### 1.1 Why routing protection is needed

In link-state networks, routers maintain a topology view and calculate
shortest paths. When a link fails, normal routing protocols must
disseminate updated link-state information and recompute forwarding
tables. The resulting convergence delay can cause packet loss and
service interruption.

Two broad approaches address this issue:

-   **Reactive recovery:** tune protocol behavior to converge more
    quickly after a failure. Aggressive tuning can risk instability,
    especially when failures are frequent or transient.
-   **Proactive protection:** calculate alternate routes in advance and
    activate them when a failure is detected.

Proactive methods differ in how they forward packets:

-   **Hop-by-hop, cooperation-free methods** give a router multiple
    candidate next hops. Routers make local forwarding decisions, so the
    resulting path must be loop-free. These methods are relatively easy
    to deploy but may leave some links unprotected.
-   **Explicit multi-hop repair methods** precompute a repair path and
    use packet-header information, special addresses, or signaling so
    that routers follow that path. These methods can provide wider
    protection coverage but add computation and coordination overhead.

### 1.2 Research objective

The paper seeks a practical balance among:

-   high network availability;
-   protection against every single-link failure;
-   low computation overhead;
-   compatibility with existing link-state routing;
-   preservation of hop-by-hop forwarding and potential load balancing
    wherever possible.

The central idea is not to use expensive multi-hop protection for every
link. Instead, use efficient loop-free alternates first, then protect
only the links that remain important to the target availability.

## 2. Related Approaches

The paper compares HLP with several families of routing-protection
mechanisms.

  -----------------------------------------------------------------------
  Approach                Main idea               Main limitation
                                                  discussed in the paper
  ----------------------- ----------------------- -----------------------
  ECMP                    Distribute traffic over Equal-cost alternatives
                          equal-cost paths        may not exist for a
                                                  failed link

  LFA / LFC               Select a neighboring    Some single-link
                          router that satisfies a failures have no usable
                          loop-free condition     alternate

  TBFH                    Improve path diversity  More computation than a
                          while retaining         single
                          loop-free forwarding    shortest-path-tree
                                                  calculation; may not
                                                  find every LFC-valid
                                                  next hop

  Routing deflection      Consider alternatives   More complex
                          beyond immediate        implementation
                          neighbors               

  Permutation routing     Create alternative      Cost grows with the
                          forwarding              number of
                          orders/configurations   configurations

  DAG-based approaches    Use directed acyclic    More complex
                          forwarding structures   computations and no
                          to avoid loops          universal alternate
                                                  guarantee

  Failure-carrying        Carry failure           Additional processing
  packets                 information in packet   and packet-format
                          headers                 implications

  Not-via / multi-hop     Route around a failure  Requires special packet
  repair                  using a precomputed     handling and
                          repair path             coordination

  MNP                     Efficiently calculate   May miss some feasible
                          multiple next hops from LFC next hops
                          one shortest-path tree  

  MNP-e                   Extend MNP to find all  Still does not by
                          feasible LFC next hops  itself protect every
                                                  single-link failure

  **HLP**                 Combine MNP-e with      Requires special
                          selective multi-hop     repair-path handling
                          backup paths            for selected links
  -----------------------------------------------------------------------

The paper's focus is on efficient computation and high protection
coverage without making multi-hop protection the default for every link.

## 3. Network Model and Availability

### 3.1 Graph representation

The network is modeled as an undirected, connected graph:

\[ G=(V,E) \]

where:

-   \(V\) is the set of routers or nodes;
-   \(E\) is the set of links;
-   (L(u,v)) is the cost of link ((u,v));
-   (r(u,v)) is the probability that link ((u,v)) is operational.

A missing link is represented by infinite cost. The model assumes that
link-failure events are statistically independent.

For a router (c), (T_c) denotes its shortest-path tree (SPT). The cost
from (c) to node (v) in this tree is denoted by (C_c(v)). The paper uses
(B_c(v)) for the preferred next hop from (c) toward (v), and (N_c(v))
for the set of candidate next hops.

### 3.2 Path and network availability

For a particular source-destination pair ((s,d)), let (p_i(s,d)) be a
possible forwarding path and (P_i(s,d)) its set of links.

Under the paper's independent-link-failure model, the probability that a
path works is the product of the operational probabilities of its links:

\[ P(A_i(s,d))=`\prod`{=tex}\_{(m,n)`\in `{=tex}P_i(s,d)} r(m,n) \]

If several forwarding paths exist, the end-to-end availability (A(s,d))
is the probability that at least one usable path works. The paper
computes this using the inclusion-exclusion principle over the
path-working events.

The network-wide availability is the average availability across all
ordered source-destination pairs:

\[ A(G)=`\frac{\sum_{s,d\in V,\;s\ne d} A(s,d)}`{=tex} {\|V\|(\|V\|-1)}
\]

This metric is used to compare protection methods and to determine
whether a specified target availability has been reached.

**Important modeling assumption:** The availability calculations depend
on the paper's independent link-failure model and on its method of
representing alternate paths. Real deployments may have correlated
failures, shared-risk link groups, or other dependencies not captured by
this model.

## 4. HLP Architecture

HLP has two stages.

### Stage 1 --- MNP-e

Each router independently calculates multiple loop-free next hops for
each destination. These alternates are used first when the router
detects that its normal next hop has failed.

### Stage 2 --- BPP

Some links may still lack a usable alternate under Stage 1. BPP
identifies those links, estimates how much protecting each one would
improve network availability, and selects links until the target
availability is met or the candidate set is exhausted.

### Forwarding after a failure

When a failure-detecting node (FDN) detects that its default next hop is
unavailable:

1.  It checks whether Stage 1 supplied another feasible next hop for the
    destination.
2.  If an alternate exists, it forwards the packet through that next
    hop.
3.  Otherwise, if the failed link is covered by BPP, it uses the
    designated multi-hop repair mechanism---for example, a not-via
    address, source routing, or another suitable signaling mechanism.
4.  Nodes receiving a packet marked for the repair path forward it along
    that path.
5.  The network synchronizes its control-plane state. Once nodes agree
    on the updated state, the protection computations are run again.

Thus, HLP combines local hop-by-hop recovery with explicit repair only
where needed.

## 5. Stage 1: Loop-Free Next-Hop Computation

### 5.1 Loop-Free Criterion (LFC)

A candidate next hop (x) at router (c), for destination (v), is valid
under the paper's LFC condition when:

\[ C_x(v) \< C_x(c)+C_c(v) \]

Intuitively, forwarding from (c) to (x) and then toward (v) must satisfy
a distance condition that prevents the packet from returning to (c). The
criterion ensures loop-free forwarding under the assumptions of the
routing model.

A straightforward way to check the condition is to construct a
shortest-path tree rooted at each neighbor. That can be expensive at
high-degree routers.

### 5.2 MNP: Multiple Next-hop Protection

MNP reduces the work by building only one shortest-path tree rooted at
the router being processed. It uses the tree's distances, parent
relationships, and best next hops to identify candidate alternates.

The paper derives a sufficient test for one node (u) to contribute its
best next hop toward a destination (v). Define:

\[ D_c(v,u)=C_c(u)-C_c(B_c(u))+L(u,v) \]

The paper's Theorem 2 states that if

\[ D_c(v,u)\<C\_{B_c(u)}(c)+C_c(v), \]

then (B_c(u)) can be added as a candidate next hop for destination (v),
while preserving loop-free forwarding.

The test can be evaluated while constructing the SPT by examining
neighboring nodes, rather than constructing a separate SPT for every
neighbor. The algorithm is similar in structure to Dijkstra's algorithm
and uses a priority queue.

**Reported complexity:** With a heap-based priority queue, MNP has time
complexity

\[ O(\|E\|`\log `{=tex}\|V\|) \]

The paper reports that MNP is efficient, but it can miss a feasible
alternate because it considers only neighbors' best next hops in its
candidate-generation process. Consequently, MNP can provide lower
availability than full LFC.

### 5.3 MNP-e: Extended MNP

MNP-e addresses MNP's coverage limitation by using **incremental
Shortest Path First (i-SPF)**.

Rather than rebuilding a shortest-path tree from scratch for every
candidate neighbor, i-SPF updates the existing tree after changing one
link's weight. In the paper's construction, the weight of the link
between the computing router (c) and a neighbor (x) is changed from
(L(c,x)) to (-L(c,x)). This transformation helps determine whether (x)
can provide a valid alternate path to a destination.

The i-SPF process, in broad terms, is:

1.  Identify nodes potentially affected by the link-weight change and
    mark them as floating.
2.  Calculate their potential new distances, parents, and distance
    changes.
3.  Repeatedly select the candidate with the most favorable distance
    change and attach the appropriate node or subtree to the updated
    tree.
4.  Continue until the updated shortest-path tree is constructed.

MNP-e repeats this incremental computation for the router's neighbors
and adds a neighbor as a candidate where the paper's conditions
establish that it is a valid LFC alternate.

The paper's theorems establish that the incremental process obtains the
correct updated SPT for the transformed link weight and that the
resulting candidate next hops satisfy the loop-free condition. The
authors state that MNP-e can find all next hops satisfying LFC without
degrading LFC's network availability.

**Complexity claim:** The paper states that MNP-e's total computation is
below the cost of constructing a full shortest-path tree, under its
analysis and assumptions. Its empirical evaluation also finds it faster
than the compared algorithms. This claim should be read in the context
of the paper's algorithm, data structures, and evaluation setup---not as
a universal guarantee for every implementation.

## 6. Stage 2: Backup Path Protection (BPP)

### 6.1 Why BPP is necessary

Even after MNP-e finds every feasible LFC alternate, some links still
cannot be protected using a local next-hop choice. HLP handles these
remaining cases through multi-hop repair paths.

A **key link** is identified when a router (v), for destination (d), has
only one candidate next hop:

\[ \|N_v(d)\|=1 \]

The corresponding link from (v) to its default next hop is considered
for protection. The paper associates each key link (e) with the
source-destination forwarding paths that depend on it.

### 6.2 Estimating a link's contribution

Let (e.P) be the set of relevant source-destination paths associated
with key link (e). The contribution of protecting that link is defined
as:

\[ `\Delta`{=tex}(e)=`\sum`{=tex}\_{(s,d)`\in `{=tex}e.P}
`\left[A^*(s,d)-A(s,d)\right]`{=tex}\]

where:

-   (A(s,d)) is the original end-to-end availability;
-   (A\^\*(s,d)) is the availability after the link is protected by its
    backup path.

To estimate (A\^\*(s,d)), BPP computes a shortest repair path in the
graph with link (e) removed, (G`\setminus `{=tex}e). The paper models
that repair by adding a pseudo-link from (s) to (d), whose availability
equals the product of the operational probabilities of the links on the
repair path. It then calculates availability on the augmented graph
using the same inclusion-exclusion approach.

### 6.3 Greedy selection procedure

BPP proceeds as follows:

1.  Each router identifies its key links and the associated paths.
2.  The key-link sets are collected and merged into a global candidate
    set (K).
3.  For each key link, BPP calculates its estimated contribution
    (`\Delta`{=tex}(e)).
4.  The candidates are sorted in descending order of contribution.
5.  Starting with the current network availability (A(G)), BPP selects
    the highest-contribution link and adds its normalized contribution
    to the availability estimate.
6.  Selection continues until the target (R) is reached or no candidates
    remain.
7.  The selected links are distributed to the network nodes, which
    coordinate the use of the corresponding repair paths.

The stopping condition is:

\[ A(G)`\ge `{=tex}R \]

or the candidate set is exhausted.

The paper deliberately considers only paths starting from the router
performing the computation when assembling (e.P), rather than
enumerating every path in the network that traverses the link. This
reduces computation. The authors argue that it conservatively
underestimates the benefit of protection because each omitted path's
individual availability improvement cannot be negative under their
model.

**Interpretation:** BPP is a greedy selection method, not a proof of a
globally optimal minimum-cardinality set for every possible topology.
Its design goal is to select a small, high-impact set of links
efficiently.

## 7. Performance Evaluation

### 7.1 Evaluation setup

The authors evaluate MNP-e and HLP on both real and generated
topologies.

**Real and inferred ISP topologies:**

  Topology     Nodes   Links
  ---------- ------- -------
  Abilene         11      14
  Exodus          79     147
  Telstra        108     153
  Tiscali        161     328
  Sprint         315     972

Synthetic topologies are generated with BRITE. The paper varies topology
size and average node degree. Link-failure probabilities are randomly
generated in the range 0 to 0.02.

The simulations were run on a PC with an Intel i5 CPU at 1.7 GHz and 1.5
GB of memory. The reported computation times are averages over nodes in
each topology.

### 7.2 Computation time on real topologies

The following table reproduces the paper's reported computation times in
microseconds.

  Network       OSPF      LFC     TBFH      MNP   DMPA-e        MNP-e
  --------- -------- -------- -------- -------- -------- ------------
  Abilene       6.82     7.27     6.97     6.83     6.87     **6.52**
  Exodus       44.36   128.29    88.76    50.23    52.67    **42.34**
  Telstra      49.45   163.43   100.34    54.34    56.73    **46.23**
  Tiscali      79.45   398.34   183.56    83.45    85.67    **75.34**
  Sprint      140.23   906.78   368.12   150.12   153.57   **137.34**

**Reported trend:** MNP-e is the fastest of the listed methods in these
tests. The difference becomes particularly clear on larger topologies.
LFC's computation time rises substantially because it computes an SPT
for each neighbor, whereas MNP-e uses incremental updates.

### 7.3 Network availability on real topologies

The paper reports the following network availability percentages:

  Network      OSPF         LFC    TBFH     MNP   DMPA-e       MNP-e
  --------- ------- ----------- ------- ------- -------- -----------
  Abilene     93.27   **97.12**   94.45   96.89    96.89   **97.12**
  Exodus      84.54   **91.25**   86.76   90.01    90.06   **91.25**
  Telstra     85.34   **93.23**   87.34   92.11    92.57   **93.23**
  Tiscali     82.12   **92.65**   84.45   90.89    91.54   **92.65**
  Sprint      81.76   **93.25**   83.45   90.13    90.97   **93.25**

MNP-e matches LFC's reported availability while using less computation.
MNP, by comparison, does not reach the same availability in these
results.

### 7.4 HLP compared with full multi-hop protection

For HLP, the paper compares the computation time and number of protected
links with a baseline that provides multi-hop backup protection for
every link.

The authors report that HLP typically needs **around 10% of the
computation time** of full multi-hop protection while achieving the
requested availability. The tested maximum availability requirement is
99.99%, which the paper describes as close to the theoretical maximum of
100%.

The proportion of links needing multi-hop backup decreases in relative
terms as topology size or density increases in the tested scenarios. The
authors attribute this to MNP-e finding more usable alternate next hops,
leaving fewer links for BPP to protect.

These are reported experimental findings, not universal performance
guarantees. The exact result depends on topology, link-failure
probabilities, target availability, and implementation.

## 8. Main Contributions

The paper's contributions can be summarized as follows:

1.  **A hybrid protection architecture:** combines local loop-free
    alternate forwarding with selective multi-hop repair.
2.  **MNP:** calculates multiple next hops from a single SPT and has
    reported complexity (O(\|E\|`\log`{=tex}\|V\|)).
3.  **MNP-e:** extends MNP using i-SPF to find all next hops satisfying
    LFC while retaining low computation overhead.
4.  **BPP:** ranks unprotected key links by their estimated contribution
    to network availability and selects links until the target is met.
5.  **Evaluation:** tests the methods on real ISP and synthetic
    topologies, comparing computation time, availability, and
    backup-link requirements.

## 9. Limitations and Assumptions to Keep in Mind

The paper's conclusions depend on several modeling and deployment
assumptions:

-   **Independent link failures:** The model assumes failure events on
    links are statistically independent. Shared-risk failures and
    correlated outages are not explicitly modeled.
-   **Single-link failure focus:** The central protection objective is
    coverage of single-link failures. This should not be interpreted as
    a general guarantee against arbitrary simultaneous multi-link
    failures.
-   **Repair-path coordination:** BPP's multi-hop protection requires a
    special packet-handling or signaling mechanism, such as not-via
    addresses or source routing.
-   **Central aggregation and coordination:** The BPP procedure gathers
    candidate key links, ranks them, and distributes the selected set.
-   **Greedy selection:** Ranking links by estimated contribution is
    computationally convenient, but the paper does not establish that
    the chosen set is globally minimum for all instances.
-   **Evaluation environment:** Computation-time results are tied to the
    paper's particular simulator/framework, hardware, topology set, and
    assumptions.
-   **Failure model is acknowledged as future work:** The authors state
    that more accurate failure modeling and deployment in hybrid
    software-defined networks are future research directions.

These qualifications do not negate the reported results; they define the
conditions under which the results should be interpreted.

## 10. Conclusion

HLP aims to achieve high availability without paying the computational
cost of multi-hop protection for every network link. MNP-e first
computes loop-free alternates efficiently. BPP then identifies the links
that remain unprotected, estimates the availability benefit of
protecting each one, and chooses a small set for multi-hop repair.

In the evaluated networks, MNP-e matches LFC's availability while
reducing computation time, and HLP reaches high target availability with
substantially less computation than full multi-hop protection. The main
engineering insight is to use inexpensive local protection wherever
possible and reserve more complex repair paths for the links where they
add the most value.

## 11. Algorithmic Workflow at a Glance

``` text
Input:
  Network graph G = (V, E)
  Link costs and failure probabilities
  Target network availability R

Stage 1 — MNP-e:
  For each router c:
    Build its shortest-path tree Tc
    For each neighbor x of c:
      Use i-SPF on the transformed link weight
      Identify additional valid loop-free next hops
    Store candidate next-hop sets Nc(v)

Stage 2 — BPP:
  Identify key links with only one candidate next hop
  Associate relevant forwarding paths with each key link
  Estimate each key link's availability contribution Δ(e)
  Sort key links by contribution, largest first
  Select links until the target availability R is reached
  Distribute the selected protection set and repair-path information

Failure handling:
  If the default next hop fails:
    Use a valid MNP-e alternate if available
    Otherwise use the configured multi-hop repair path
  Synchronize routing state and recompute protection after convergence
```

## 12. Glossary

-   **Availability:** Probability that packets can be forwarded
    successfully between a source and destination, or the average of
    this probability over all source-destination pairs.
-   **BPP (Backup Path Protection):** HLP's second stage; selects key
    links for multi-hop repair.
-   **FDN (Failure-Detecting Node):** Router that detects a failure
    affecting its next hop.
-   **HLP (Hybrid Link Protection):** The complete two-stage protection
    scheme.
-   **i-SPF (Incremental Shortest Path First):** Updates a shortest-path
    tree using an existing tree rather than rebuilding it entirely.
-   **LFC (Loop-Free Criterion):** Condition used to select alternate
    next hops that avoid forwarding loops.
-   **LFA (Loop-Free Alternate):** An alternate next hop satisfying a
    loop-free condition.
-   **MNP (Multiple Next-hop Protection):** Efficient single-SPT
    approach for finding candidate next hops.
-   **MNP-e:** Extension of MNP that aims to find all feasible LFC next
    hops.
-   **OSPF / IS-IS:** Link-state interior gateway routing protocols.
-   **SPT (Shortest-Path Tree):** Tree of shortest paths from one root
    router to the other nodes.
-   **Key link:** In BPP, a link associated with a destination for which
    only one candidate next hop is available.
-   **Repair path:** Precomputed multi-hop path used to route around a
    failed link.

## Source

Geng, H., Zhang, H., Shi, X., Wang, Z., Yin, X., Zhang, J., Hu, Z., &
Wu, Y. (2020). "A Hybrid Link Protection Scheme for Ensuring Network
Service Availability in Link-state Routing Networks." *Journal of
Communications and Networks*, 22(1), 46--60.
https://doi.org/10.1109/JCN.2019.000056
