# Paper (Networking / Routing)

### Base Paper

**A Hybrid Link Protection Scheme for Ensuring Network Service Availability in Link-State Routing Networks**
https://ieeexplore.ieee.org/document/9042897

### My Research Direction

Instead of reproducing HLP, extend it.

### Proposed Title

**Adaptive Hybrid Link Protection for Failure-Resilient Link-State Routing Networks**

or

**An Enhanced Hybrid Link Protection Scheme for Efficient Network Service Availability**


This research project focuses on **improving network service availability in link-state routing networks during link failures**. The base paper is *A Hybrid Link Protection Scheme for Ensuring Network Service Availability in Link-State Routing Networks* (IEEE 9042897). I will first implement and reproduce its **LFC, MNP-e, BPP, and HLP** algorithms, then investigate an enhancement that can provide full failure protection with lower computational and backup-path overhead.


### Possible Contributions

* Adaptive backup path selection based on current traffic
* Improved critical-link selection algorithm
* Reduced backup path overhead
* Lower computation time than the original HLP
* Better load balancing during failures
* Evaluation on larger or more realistic topologies

### Tools

* Python
* NetworkX
* Internet Topology Zoo / Rocketfuel datasets
* Mininet (optional)
* FRRouting (future work)

### Metrics

* Network Availability
* Recovery Time
* Packet Loss
* Protected Links
* CPU Time
* Memory Overhead


## Hybrid Link Protection (HLP)

```
hlp/
├── data/
├── topology.py          # Graph representation
├── shortest_path.py     # Dijkstra
├── lfc.py               # Loop-Free Criterion
├── mnp_e.py             # Stage 1
├── bpp.py               # Stage 2
├── packet.py            # Packet simulation
├── simulator.py         # Failure simulator
├── metrics.py           # Availability calculations
├── visualization.py     # Graph visualization
├── main.py
└── tests/
```

### Development Roadmap

1. Graph representation
2. Dijkstra SPF
3. Failure simulation
4. LFC implementation
5. MNP-e implementation
6. BPP implementation
7. HLP integration
8. Evaluation