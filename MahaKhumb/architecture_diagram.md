# Architecture Diagram

```mermaid
flowchart LR
    A["OpenStreetMap / Synthetic Fallback"] --> B["Layer 1: Weighted Walk Network"]
    B --> B2["Synthetic / Forecasted Node Pressure"]
    B2 --> C["Betweenness Centrality Scan"]
    C --> D["Layer 2: K-Means Zone Decomposition"]
    D --> E["Intra-Zone Candidate OD Groups"]
    E --> E2["Alternative Route Set Per Group"]
    D --> F["Inter-Zone Distance Matrix"]
    E2 --> G["Layer 3: QAOA Route Assignment QUBO"]
    E2 --> H["Exact Brute-Force Baseline"]
    E2 --> H2["Greedy Classical Heuristic"]
    F --> I["Inter-Zone Backbone Selection"]
    G --> J["Comparison and Reporting"]
    H --> J
    H2 --> J
    I --> J
    J --> K["Judge-Ready PNG / JSON / Markdown Artifacts"]
```

## Layer Summary

- Layer 1 builds a real, weighted walk network around Prayagraj.
- Layer 1 also injects forecasted pressure into edge weights before downstream routing benchmarks.
- Layer 2 compresses the graph into operational zones and derives local origin-destination cohorts.
- Layer 3 compares QAOA against exact and greedy classical baselines on a binary route-assignment problem inside each zone.
- The current architecture is a benchmark scaffold for local multi-group routing, not a finished city-scale crowd-flow optimizer.
