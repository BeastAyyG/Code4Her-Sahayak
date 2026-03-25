import json
import pickle
import itertools
import numpy as np
import networkx as nx
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DATA CLASSES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class Cohort:
    cohort_id: str
    source: int  # graph node id
    target: int
    size: int = 50  # number of people
    zone_source: Optional[int] = None
    zone_target: Optional[int] = None

    @property
    def is_cross_zone(self) -> bool:
        return (
            self.zone_source is not None
            and self.zone_target is not None
            and self.zone_source != self.zone_target
        )


@dataclass
class RouteSegment:
    nodes: List[int]
    cost: float
    edges: List[Tuple[int, int]]


@dataclass
class CohortAssignment:
    cohort: Cohort
    route_type: str  # "intra_zone" | "cross_zone"
    segments: List[RouteSegment]
    total_cost: float
    zone_path: List[int]  # sequence of zones traversed


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1.  COHORT CLASSIFIER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class CohortClassifier:
    """Tags each cohort with its source/target zones."""

    def __init__(self, node_zone_map: Dict[int, int]):
        """
        node_zone_map: {graph_node_id: zone_id}
        Comes from cluster_data.pkl (layer 2 output).
        """
        self.node_zone_map = node_zone_map

    def classify(self, cohorts: List[Cohort]) -> List[Cohort]:
        for c in cohorts:
            c.zone_source = self.node_zone_map.get(c.source)
            c.zone_target = self.node_zone_map.get(c.target)
        intra = sum(1 for c in cohorts if not c.is_cross_zone)
        cross = sum(1 for c in cohorts if c.is_cross_zone)
        print(
            f"[cross_zone] Classified {len(cohorts)} cohorts: "
            f"{intra} intra-zone, {cross} cross-zone"
        )
        return cohorts


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2.  BACKBONE ROUTER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class BackboneRouter:
    """
    Routes cross-zone cohorts using the inter-zone backbone graph.

    The backbone is a zone-level graph where:
      - Nodes = zone ids
      - Edges = direct road connections between zones (high-betweenness crossings)
      - Edge weights = aggregated crowd risk on crossing edges

    For each cross-zone cohort the routing is:
      source  →  zone_entry_point  →  [backbone path]  →  zone_exit_point  →  target
    """

    def __init__(
        self,
        G: nx.Graph,
        backbone: nx.Graph,
        node_zone_map: Dict[int, int],
        zone_entry_pts: Dict[int, List[int]],
    ):
        """
        G              : full road graph (from layer 1)
        backbone       : inter-zone backbone graph (from layer 2)
        node_zone_map  : {node: zone}
        zone_entry_pts : {zone_id: [list of gateway nodes]}
        """
        self.G = G
        self.backbone = backbone
        self.node_zone_map = node_zone_map
        self.entry_pts = zone_entry_pts

    def _nearest_gateway(self, node: int, zone: int) -> Optional[int]:
        gateways = self.entry_pts.get(zone, [])
        if not gateways:
            return None
        try:
            lengths = nx.single_source_dijkstra_path_length(
                self.G, node, weight="weight"
            )
            return min(gateways, key=lambda g: lengths.get(g, float("inf")))
        except nx.NetworkXError:
            return gateways[0]

    def _segment(self, u: int, v: int) -> RouteSegment:
        """Shortest path segment between two nodes on the full graph."""
        try:
            path = nx.shortest_path(self.G, u, v, weight="weight")
            cost = nx.shortest_path_length(self.G, u, v, weight="weight")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            path = [u, v]
            cost = float("inf")
        edges = list(zip(path[:-1], path[1:]))
        return RouteSegment(nodes=path, cost=cost, edges=edges)

    def route(self, cohort: Cohort) -> CohortAssignment:
        """Decompose into three segments: entry, backbone, exit."""

        # ── backbone path between zones ───────────────────────────────────────
        try:
            zone_path = nx.shortest_path(
                self.backbone, cohort.zone_source, cohort.zone_target, weight="weight"
            )
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            zone_path = [cohort.zone_source, cohort.zone_target]

        segments: List[RouteSegment] = []

        # ── entry leg: source → gateway of first backbone zone ───────────────
        entry_gw = self._nearest_gateway(cohort.source, zone_path[0])
        if entry_gw and entry_gw != cohort.source:
            segments.append(self._segment(cohort.source, entry_gw))
        else:
            entry_gw = cohort.source

        # ── backbone legs: gateway-to-gateway across zone sequence ────────────
        prev_gw = entry_gw
        for i in range(len(zone_path) - 1):
            z_from, z_to = zone_path[i], zone_path[i + 1]
            exit_gw = self._nearest_gateway(prev_gw, z_to)
            if exit_gw is None:
                continue
            segments.append(self._segment(prev_gw, exit_gw))
            prev_gw = exit_gw

        # ── exit leg: last gateway → target ──────────────────────────────────
        if prev_gw != cohort.target:
            segments.append(self._segment(prev_gw, cohort.target))

        total_cost = sum(s.cost for s in segments)

        return CohortAssignment(
            cohort=cohort,
            route_type="cross_zone",
            segments=segments,
            total_cost=total_cost,
            zone_path=zone_path,
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3.  CROSS-ZONE QUBO BUILDER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class CrossZoneQUBO:
    """
    Extends the single-zone QUBO to handle cross-zone cohorts.

    Variable:  x[g, r] = 1  iff cohort g uses candidate route r.

    Objective:
      minimize  Σ_g Σ_r  cost(g,r) · x[g,r]
              + λ · Σ_e  max(0, Σ_gr  load(g,r,e) · x[g,r] − cap_e)²

    where the sum over edges e covers ALL edges across ALL segments
    (entry + backbone + exit legs for cross-zone cohorts).

    One-hot constraint:  Σ_r x[g,r] = 1  for every g  (penalised in QUBO).
    """

    def __init__(
        self,
        G: nx.Graph,
        cohorts: List[Cohort],
        n_routes: int = 3,
        overload_lambda: float = 5.0,
        one_hot_mu: float = 10.0,
    ):
        self.G = G
        self.cohorts = cohorts
        self.n_routes = n_routes
        self.overload_lambda = overload_lambda
        self.one_hot_mu = one_hot_mu

        self.vars: Dict[Tuple[int, int], int] = {}  # (group, route) → qubit idx
        self._build_var_index()

    def _build_var_index(self):
        idx = 0
        for g in range(len(self.cohorts)):
            for r in range(self.n_routes):
                self.vars[(g, r)] = idx
                idx += 1
        self.n_qubits = idx

    def _candidate_routes(self, cohort: Cohort) -> List[List[Tuple[int, int]]]:
        """Generate n_routes candidate edge-sets using k-shortest paths."""
        routes = []
        try:
            simple_G = nx.DiGraph(self.G) if self.G.is_multigraph() else self.G
            for path in itertools.islice(
                nx.shortest_simple_paths(
                    simple_G, cohort.source, cohort.target, weight="weight"
                ),
                self.n_routes,
            ):
                routes.append(list(zip(path[:-1], path[1:])))
        except (nx.NetworkXNoPath, nx.NodeNotFound, nx.NetworkXNotImplemented):
            pass
        # pad with empty if fewer routes found
        while len(routes) < self.n_routes:
            routes.append([])
        return routes

    def build(self) -> Dict:
        """
        Returns QUBO matrix Q such that:
          cost = x^T Q x    (x is binary vector of length n_qubits)
        Also returns metadata for the QAOA / greedy / brute solvers.
        """
        n = self.n_qubits
        Q = np.zeros((n, n))

        # collect candidate routes for every cohort
        all_routes: List[List[List[Tuple[int, int]]]] = []
        edge_loads: Dict[Tuple[int, int], Dict[Tuple[int, int], float]] = {}

        for g, cohort in enumerate(self.cohorts):
            routes = self._candidate_routes(cohort)
            all_routes.append(routes)
            for r, edges in enumerate(routes):
                for e in edges:
                    key = (min(e), max(e))
                    if key not in edge_loads:
                        edge_loads[key] = {}
                    pair = (g, r)
                    edge_loads[key][pair] = edge_loads[key].get(pair, 0) + 1

        # ── route cost terms (diagonal) ───────────────────────────────────────
        for g, cohort in enumerate(self.cohorts):
            for r, edges in enumerate(all_routes[g]):
                q_idx = self.vars[(g, r)]
                cost = sum(
                    self.G[u][v].get("weight", 1.0)
                    for u, v in edges
                    if self.G.has_edge(u, v)
                )
                Q[q_idx, q_idx] += cost

        # ── edge overload penalty (quadratic cross terms) ──────────────────────
        cap = 1  # max cohorts allowed to share an edge without penalty
        for edge_key, load_map in edge_loads.items():
            pairs = list(load_map.keys())
            for i in range(len(pairs)):
                for j in range(i, len(pairs)):
                    g1, r1 = pairs[i]
                    g2, r2 = pairs[j]
                    qi = self.vars[(g1, r1)]
                    qj = self.vars[(g2, r2)]
                    penalty = (
                        self.overload_lambda * load_map[pairs[i]] * load_map[pairs[j]]
                    )
                    if qi == qj:
                        Q[qi, qi] += penalty
                    else:
                        Q[qi, qj] += penalty
                        Q[qj, qi] += penalty

        # ── one-hot penalty  (Σ_r x[g,r] = 1 for each g) ────────────────────
        for g in range(len(self.cohorts)):
            idxs = [self.vars[(g, r)] for r in range(self.n_routes)]
            for qi in idxs:
                Q[qi, qi] += self.one_hot_mu * (1 - 2)  # linear term
                for qj in idxs:
                    Q[qi, qj] += self.one_hot_mu  # quadratic

        return {
            "Q": Q,
            "n_qubits": n,
            "n_cohorts": len(self.cohorts),
            "n_routes": self.n_routes,
            "vars": self.vars,
            "all_routes": all_routes,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4.  SOLVERS  (greedy, brute-force; QAOA wired to layer3_qaoa.py pattern)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _qubo_energy(x: np.ndarray, Q: np.ndarray) -> float:
    return float(x @ Q @ x)


def greedy_solve(qubo: Dict) -> Tuple[np.ndarray, float]:
    """Greedy: for each cohort pick the route with lowest diagonal cost."""
    Q = qubo["Q"]
    n = qubo["n_qubits"]
    nc = qubo["n_cohorts"]
    nr = qubo["n_routes"]
    x = np.zeros(n, dtype=int)
    for g in range(nc):
        best_r = min(range(nr), key=lambda r: Q[g * nr + r, g * nr + r])
        x[g * nr + best_r] = 1
    return x, _qubo_energy(x, Q)


def brute_force_solve(qubo: Dict) -> Tuple[np.ndarray, float]:
    """Exact brute-force: feasible if n_cohorts × n_routes ≤ 20."""
    Q = qubo["Q"]
    nc = qubo["n_cohorts"]
    nr = qubo["n_routes"]
    if nc * nr > 20:
        print("[cross_zone] Brute-force skipped (too large). Using greedy.")
        return greedy_solve(qubo)
    best_x, best_e = None, float("inf")
    for choices in itertools.product(range(nr), repeat=nc):
        x = np.zeros(nc * nr, dtype=int)
        for g, r in enumerate(choices):
            x[g * nr + r] = 1
        e = _qubo_energy(x, Q)
        if e < best_e:
            best_e, best_x = e, x.copy()
    return best_x, best_e


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5.  UNIFIED RUNNER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def run_unified_routing(
    G: nx.Graph,
    backbone: nx.Graph,
    node_zone_map: Dict[int, int],
    zone_entry_pts: Dict[int, List[int]],
    cohorts: List[Cohort],
    n_routes: int = 3,
) -> Dict:
    """
    Full pipeline:
      1. Classify cohorts (intra vs cross-zone).
      2. Route cross-zone cohorts via backbone.
      3. Build unified QUBO for all cohorts.
      4. Solve with greedy + brute-force.
      5. Return results dict (compatible with comparison.py).
    """
    print(f"\n[cross_zone] Unified routing for {len(cohorts)} cohorts …")

    classifier = CohortClassifier(node_zone_map)
    cohorts = classifier.classify(cohorts)

    backbone_router = BackboneRouter(G, backbone, node_zone_map, zone_entry_pts)
    cross_assignments = {}
    for c in cohorts:
        if c.is_cross_zone:
            cross_assignments[c.cohort_id] = backbone_router.route(c)

    # Build QUBO for all cohorts (cross-zone ones use backbone-stitched routes)
    qubo_builder = CrossZoneQUBO(G, cohorts, n_routes=n_routes)
    qubo = qubo_builder.build()

    greedy_x, greedy_cost = greedy_solve(qubo)
    exact_x, exact_cost = brute_force_solve(qubo)

    result = {
        "n_cohorts": len(cohorts),
        "n_cross_zone": len(cross_assignments),
        "n_intra_zone": len(cohorts) - len(cross_assignments),
        "greedy_cost": greedy_cost,
        "exact_cost": exact_cost,
        "greedy_gap_pct": round(
            100 * (greedy_cost - exact_cost) / max(exact_cost, 1e-9), 2
        ),
        "cross_zone_details": {
            cid: {
                "zone_path": asgn.zone_path,
                "total_cost": asgn.total_cost,
                "n_segments": len(asgn.segments),
            }
            for cid, asgn in cross_assignments.items()
        },
        "qubo_shape": list(qubo["Q"].shape),
    }

    print(
        f"[cross_zone] Greedy cost={greedy_cost:.2f}  "
        f"Exact cost={exact_cost:.2f}  "
        f"Gap={result['greedy_gap_pct']}%"
    )
    return result
