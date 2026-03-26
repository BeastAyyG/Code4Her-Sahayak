# Slide Deck Draft

## Slide 1: Title

**Quantum-Assisted Multi-Group Routing Benchmark for MahaKumbh**

- Continuum sprint demo
- Real map + zoning + QAOA routing

## Slide 2: The Emergency Routing Problem
- Kumbh Mela crowds create dynamically changing, highly congested chokepoints.
- Static shortest-path routing can miss pressure hotspots and corridor risk.
- Our current benchmark objective: assign multiple high-risk local cohorts to alternative routes inside each operational zone while penalizing shared-edge overload.
- Be explicit: this is a local route-assignment benchmark, not a full city-scale flow deployment.

## Slide 3: Architecture

- Use [architecture_diagram.md](C:/Users/ramkr/code%20for%20her/code4her/Continuum/architecture_diagram.md)
- Emphasize the 3-layer hybrid design.

## Slide 4: Real Prayagraj Graph

- Use [output_layer1_network.png](C:/Users/ramkr/code%20for%20her/code4her/Continuum/output_layer1_network.png)
- Mention the current verified run: 770 nodes, 1852 edges.

## Slide 5: Zone Decomposition

- Use [output_layer2_clusters.png](C:/Users/ramkr/code%20for%20her/code4her/Continuum/output_layer2_clusters.png)
- 40 important intersections reduced into 8 zones.

## Slide 6: Quantum vs Classical

- Use [output_barchart.png](C:/Users/ramkr/code%20for%20her/code4her/Continuum/output_barchart.png)
- Current run: QAOA is compared against brute-force optimum and greedy assignment on the same binary route-allocation objective.
- That honesty helps, because the benchmark reports feasibility instead of hiding failures.

## Slide 7: Operational View

- Use [output_route_overlay.png](C:/Users/ramkr/code%20for%20her/code4her/Continuum/output_route_overlay.png)
- Show local routes and backbone logic as a control-room friendly picture.

## Slide 8: The Quantum Scaling Trajectory (Honesty Matters)
- **Current Reality**: On 4-node zones, classical exact search is trivial. This is a benchmark regime, not a speedup regime.
- **Why Quantum Is Still Relevant**: The assignment QUBO grows with `groups x route options`, and repeated re-optimization under shared-edge penalties becomes combinatorial.
- **What We Actually Claim**: This repository demonstrates the benchmark scaffold, noise-aware QAOA evaluation, and the hardware-scaling roadmap for multi-group local routing.
- Applicability: local diversion planning, responder corridor allocation, zone-level crowd balancing.

## Slide 9: Impact and Honesty

- No claim of present-day quantum speedup.
- Strong claim: real map, working hybrid architecture, exact baseline, explicit limitations, clear upgrade path.
- If challenged, say plainly: "The classical pipeline identifies hotspot zones; the quantum layer benchmarks multi-group route assignment within those zones."
