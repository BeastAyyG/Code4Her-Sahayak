# Presentation Outline

## Slide 1: Title
- Quantum-Enhanced Crowd Optimization for Mega Events
- MahaKhumb sprint demo

## Slide 2: Problem
- Kumbh Mela creates extreme crowd-density and routing pressure.
- Static shortest-path routing is not enough when congestion and safety matter together.

## Slide 3: Architecture
- Layer 1: Real walk network around Sangam from OpenStreetMap.
- Layer 2: Betweenness-driven K-Means zoning.
- Layer 3: QAOA on capped subproblems plus classical baseline.

## Slide 4: Real Map
- Use `output_layer1_network.png`
- Mention live OSM extraction with synthetic fallback for demo resilience.

## Slide 5: Zone Decomposition
- Use `output_layer2_clusters.png`
- Mention 40 key intersections decomposed into 8 manageable zones.

## Slide 6: Results
- Use `output_barchart.png` and `output_comparison.png`
- Current run: QAOA matched exact baseline on 4 solved zones.

## Slide 7: Impact
- Hierarchical quantum-ready routing for mega-events.
- Adaptable to pilgrimages, festivals, stadium exits, and evacuation planning.

## Defense Notes
- Why QAOA:
  Routing with multiple competing objectives becomes combinatorial. QAOA is a natural fit for QUBO-style optimization.
- Why clustering first:
  NISQ-era quantum methods cannot take the full city graph directly. Clustering reduces the problem into solvable local subproblems.
- Why not only Dijkstra:
  Dijkstra solves a fixed shortest-path objective. This pipeline is structured for congestion-aware multi-criteria optimization.
- What is the QUBO:
  Binary variables `x_{i,t}` represent node `i` at route position `t`, with penalty terms enforcing valid tours.
- Is there quantum advantage today:
  Not on these tiny subproblems. The current value is proof of method, architecture, and hybrid decomposition.
