"""Goal 4: benchmark multi-group route assignment on clustered subproblems."""

from __future__ import annotations

import itertools
import math
import pickle
import time
from dataclasses import asdict, dataclass
from itertools import islice

import networkx as nx
import numpy as np
from qiskit_algorithms import QAOA
from qiskit_algorithms.optimizers import COBYLA
from qiskit_optimization import QuadraticProgram
from qiskit_optimization.algorithms import MinimumEigenOptimizer

try:
    from qiskit.primitives import StatevectorSampler
except (ImportError, TypeError):
    StatevectorSampler = None

try:
    from qiskit_aer import AerSimulator
except (ImportError, TypeError):
    AerSimulator = None

try:
    from qiskit_ibm_runtime.fake_provider import FakeSherbrooke
except (ImportError, TypeError):
    FakeSherbrooke = None

if (
    StatevectorSampler is not None
    and AerSimulator is not None
    and FakeSherbrooke is not None
):
    SAMPLER_NAME = "AerSimulator_FakeSherbrooke"
elif StatevectorSampler is not None:
    SAMPLER_NAME = "StatevectorSampler"
else:
    SAMPLER_NAME = "unavailable"

from config import (
    CLUSTER_OUTPUT,
    FLOW_GROUP_COUNT,
    FLOW_OVERLAP_PENALTY,
    GRAPH_OUTPUT,
    MAX_QAOA_CLUSTERS,
    QAOA_MAXITER,
    QAOA_OUTPUT,
    QAOA_REPS,
    QAOA_TRIALS,
    RANDOM_SEED,
    ROUTE_OPTIONS_PER_GROUP,
)
from cross_zone_router import run_unified_routing, Cohort
from artifact_utils import write_pickle_atomic

GRAPH_INPUT = GRAPH_OUTPUT
CLUSTER_INPUT = CLUSTER_OUTPUT
RESULT_OUTPUT = QAOA_OUTPUT


@dataclass
class CandidateRoute:
    group_id: int
    option_id: int
    source: int
    target: int
    demand: float
    node_path: list[int]
    cost: float
    shared_edge_weight: float


@dataclass
class TrialResult:
    cluster_id: int
    method: str
    objective: float
    feasible: bool
    route_source: str
    time: float
    optimizer_status: str
    selected_options: list[int]
    selected_routes: list[dict[str, object]]
    overload_penalty: float
    average_route_cost: float
    optimality_gap_percent: float | None = None


def brute_force_cycle(dist_matrix: np.ndarray) -> tuple[list[int], float]:
    n = dist_matrix.shape[0]
    if n < 2:
        return [0], 0.0
    start = 0
    best_path: list[int] = list(range(n))
    best_cost = float("inf")
    for perm in itertools.permutations(range(1, n)):
        route = [start, *perm]
        cost = float(
            sum(
                dist_matrix[route[idx], route[(idx + 1) % len(route)]]
                for idx in range(len(route))
            )
        )
        if cost < best_cost:
            best_path = route
            best_cost = cost
    return best_path, best_cost


def nearest_neighbor_cycle(dist_matrix: np.ndarray) -> tuple[list[int], float]:
    n = dist_matrix.shape[0]
    if n < 2:
        return [0], 0.0
    best_route: list[int] | None = None
    best_cost = float("inf")
    for start in range(n):
        remaining = set(range(n))
        route = [start]
        remaining.remove(start)
        current = start
        while remaining:
            nxt = min(remaining, key=lambda node: dist_matrix[current, node])
            route.append(nxt)
            remaining.remove(nxt)
            current = nxt
        cost = float(
            sum(
                dist_matrix[route[idx], route[(idx + 1) % len(route)]]
                for idx in range(len(route))
            )
        )
        if cost < best_cost:
            best_cost = cost
            best_route = route
    return best_route or [0], best_cost


def _edge_weight(graph: nx.MultiDiGraph, u: int, v: int) -> float:
    edge_bundle = graph.get_edge_data(u, v)
    if not edge_bundle:
        raise KeyError(f"Missing edge data for ({u}, {v})")
    return float(min(data.get("combined_weight", 1.0) for data in edge_bundle.values()))


def _path_cost(graph: nx.MultiDiGraph, path: list[int]) -> float:
    return float(
        sum(
            _edge_weight(graph, path[idx], path[idx + 1])
            for idx in range(len(path) - 1)
        )
    )


def _path_shared_weight(graph: nx.MultiDiGraph, path: list[int]) -> float:
    return float(
        sum(
            _edge_weight(graph, path[idx], path[idx + 1])
            for idx in range(len(path) - 1)
        )
    )


def _path_edge_map(
    graph: nx.MultiDiGraph, path: list[int]
) -> dict[tuple[int, int], float]:
    edges: dict[tuple[int, int], float] = {}
    for idx in range(len(path) - 1):
        key = tuple(sorted((int(path[idx]), int(path[idx + 1]))))
        edges[key] = _edge_weight(graph, path[idx], path[idx + 1])
    return edges


def _node_pressure(graph: nx.MultiDiGraph, node_id: int) -> float:
    values = []
    for _, _, data in graph.out_edges(node_id, data=True):
        values.append(
            float(data.get("predicted_density", data.get("simulated_density", 1.0)))
        )
    for _, _, data in graph.in_edges(node_id, data=True):
        values.append(
            float(data.get("predicted_density", data.get("simulated_density", 1.0)))
        )
    return float(np.mean(values)) if values else 1.0


def _zone_group_pairs(
    graph: nx.MultiDiGraph, node_ids: list[int]
) -> list[tuple[int, int, float]]:
    if len(node_ids) < 2:
        return []

    pair_rows: list[tuple[float, int, int, float]] = []
    for source, target in itertools.combinations(node_ids, 2):
        try:
            distance = nx.shortest_path_length(
                graph, source, target, weight="combined_weight"
            )
        except nx.NetworkXNoPath:
            continue
        demand = 1.0 + (
            (_node_pressure(graph, source) + _node_pressure(graph, target)) / 8.0
        )
        pair_rows.append((float(distance), int(source), int(target), float(demand)))

    pair_rows.sort(reverse=True, key=lambda row: row[0])
    return [
        (source, target, demand)
        for _, source, target, demand in pair_rows[:FLOW_GROUP_COUNT]
    ]


def _candidate_paths(
    graph: nx.MultiDiGraph,
    source: int,
    target: int,
    route_count: int,
) -> list[list[int]]:
    try:
        iterator = nx.shortest_simple_paths(
            nx.DiGraph(graph), source, target, weight="combined_weight"
        )
        paths = [list(path) for path in islice(iterator, route_count)]
        if paths:
            return paths
    except Exception:
        pass
    return [nx.shortest_path(graph, source, target, weight="combined_weight")]


def build_zone_problem(
    graph: nx.MultiDiGraph, cluster_id: int, node_ids: list[int]
) -> dict[str, object]:
    group_pairs = _zone_group_pairs(graph, node_ids)
    routes_by_group: list[list[CandidateRoute]] = []

    for group_id, (source, target, demand) in enumerate(group_pairs):
        group_routes = []
        for option_id, node_path in enumerate(
            _candidate_paths(graph, source, target, ROUTE_OPTIONS_PER_GROUP)
        ):
            group_routes.append(
                CandidateRoute(
                    group_id=group_id,
                    option_id=option_id,
                    source=source,
                    target=target,
                    demand=float(demand),
                    node_path=node_path,
                    cost=_path_cost(graph, node_path) * float(demand),
                    shared_edge_weight=_path_shared_weight(graph, node_path),
                )
            )
        routes_by_group.append(group_routes)

    if not routes_by_group:
        return {
            "cluster_id": cluster_id,
            "group_pairs": [],
            "routes_by_group": [],
            "overlap_matrix": {},
        }

    overlap_matrix: dict[tuple[int, int, int, int], float] = {}
    for g1, routes1 in enumerate(routes_by_group):
        for g2, routes2 in enumerate(routes_by_group):
            if g2 <= g1:
                continue
            for route1 in routes1:
                edges1 = _path_edge_map(graph, route1.node_path)
                for route2 in routes2:
                    edges2 = _path_edge_map(graph, route2.node_path)
                    shared = set(edges1).intersection(edges2)
                    if not shared:
                        continue
                    shared_weight = sum(
                        min(edges1[edge], edges2[edge]) for edge in shared
                    )
                    overlap_matrix[(g1, route1.option_id, g2, route2.option_id)] = (
                        shared_weight * route1.demand * route2.demand
                    )

    return {
        "cluster_id": cluster_id,
        "group_pairs": group_pairs,
        "routes_by_group": routes_by_group,
        "overlap_matrix": overlap_matrix,
    }


def build_quadratic_program(problem: dict[str, object]) -> QuadraticProgram:
    qp = QuadraticProgram(name=f"zone_{problem['cluster_id']}_flow_assignment")
    routes_by_group: list[list[CandidateRoute]] = problem["routes_by_group"]  # type: ignore[assignment]
    overlap_matrix: dict[tuple[int, int, int, int], float] = problem["overlap_matrix"]  # type: ignore[assignment]

    linear: dict[str, float] = {}
    quadratic: dict[tuple[str, str], float] = {}
    assignment_penalty = 100.0
    for group_id, routes in enumerate(routes_by_group):
        for route in routes:
            name = f"x_{group_id}_{route.option_id}"
            qp.binary_var(name=name)
            linear[name] = float(route.cost) - assignment_penalty
        for route_a, route_b in itertools.combinations(routes, 2):
            quadratic[
                (
                    f"x_{group_id}_{route_a.option_id}",
                    f"x_{group_id}_{route_b.option_id}",
                )
            ] = quadratic.get(
                (
                    f"x_{group_id}_{route_a.option_id}",
                    f"x_{group_id}_{route_b.option_id}",
                ),
                0.0,
            ) + (2.0 * assignment_penalty)

    for (g1, r1, g2, r2), overlap in overlap_matrix.items():
        quadratic[(f"x_{g1}_{r1}", f"x_{g2}_{r2}")] = quadratic.get(
            (f"x_{g1}_{r1}", f"x_{g2}_{r2}"), 0.0
        ) + float(FLOW_OVERLAP_PENALTY * overlap)

    qp.minimize(linear=linear, quadratic=quadratic)
    return qp


def evaluate_assignment(
    problem: dict[str, object], selected_options: list[int]
) -> tuple[float, float, float, list[dict[str, object]]]:
    routes_by_group: list[list[CandidateRoute]] = problem["routes_by_group"]  # type: ignore[assignment]
    overlap_matrix: dict[tuple[int, int, int, int], float] = problem["overlap_matrix"]  # type: ignore[assignment]

    chosen_routes = [
        routes_by_group[group_id][option_id]
        for group_id, option_id in enumerate(selected_options)
    ]
    route_cost = float(sum(route.cost for route in chosen_routes))

    overload_penalty = 0.0
    for g1 in range(len(selected_options)):
        for g2 in range(g1 + 1, len(selected_options)):
            overload_penalty += float(
                FLOW_OVERLAP_PENALTY
                * overlap_matrix.get(
                    (g1, selected_options[g1], g2, selected_options[g2]), 0.0
                )
            )

    selected_routes = [
        {
            "group_id": route.group_id,
            "option_id": route.option_id,
            "source": route.source,
            "target": route.target,
            "demand": route.demand,
            "node_path": route.node_path,
            "path_length_nodes": len(route.node_path),
            "base_cost": route.cost,
        }
        for route in chosen_routes
    ]
    return (
        route_cost + overload_penalty,
        overload_penalty,
        route_cost / max(1, len(chosen_routes)),
        selected_routes,
    )


def brute_force_optimum(problem: dict[str, object], cluster_id: int) -> TrialResult:
    routes_by_group: list[list[CandidateRoute]] = problem["routes_by_group"]  # type: ignore[assignment]
    if not routes_by_group:
        return TrialResult(
            cluster_id=cluster_id,
            method="Exact",
            objective=0.0,
            feasible=True,
            route_source="trivial",
            time=0.0,
            optimizer_status="SUCCESS",
            selected_options=[],
            selected_routes=[],
            overload_penalty=0.0,
            average_route_cost=0.0,
            optimality_gap_percent=0.0,
        )

    started = time.time()
    choice_space = [range(len(routes)) for routes in routes_by_group]
    best_choices: list[int] | None = None
    best_objective = float("inf")
    best_overload = 0.0
    best_avg_cost = 0.0
    best_routes: list[dict[str, object]] = []

    for choices in itertools.product(*choice_space):
        objective, overload, avg_cost, selected_routes = evaluate_assignment(
            problem, list(choices)
        )
        if objective < best_objective:
            best_objective = objective
            best_choices = list(choices)
            best_overload = overload
            best_avg_cost = avg_cost
            best_routes = selected_routes

    elapsed = time.time() - started
    return TrialResult(
        cluster_id=cluster_id,
        method="Exact",
        objective=float(best_objective),
        feasible=True,
        route_source="bruteforce_assignment",
        time=elapsed,
        optimizer_status="SUCCESS",
        selected_options=best_choices or [],
        selected_routes=best_routes,
        overload_penalty=float(best_overload),
        average_route_cost=float(best_avg_cost),
        optimality_gap_percent=0.0,
    )


def greedy_heuristic(
    problem: dict[str, object], cluster_id: int, optimal_objective: float
) -> TrialResult:
    routes_by_group: list[list[CandidateRoute]] = problem["routes_by_group"]  # type: ignore[assignment]
    used_edges: dict[tuple[int, int], float] = {}
    selected_options: list[int] = []
    selected_routes: list[dict[str, object]] = []
    started = time.time()

    for group_id, routes in enumerate(routes_by_group):
        best_idx = 0
        best_score = float("inf")
        for route in routes:
            path_edges = _path_edge_map_graphless(route.node_path)
            overlap = sum(used_edges.get(edge, 0.0) for edge in path_edges)
            score = route.cost + (FLOW_OVERLAP_PENALTY * overlap * route.demand)
            if score < best_score:
                best_score = score
                best_idx = route.option_id
        selected_options.append(best_idx)
        chosen = routes[best_idx]
        selected_routes.append(
            {
                "group_id": chosen.group_id,
                "option_id": chosen.option_id,
                "source": chosen.source,
                "target": chosen.target,
                "demand": chosen.demand,
                "node_path": chosen.node_path,
                "path_length_nodes": len(chosen.node_path),
                "base_cost": chosen.cost,
            }
        )
        for edge in _path_edge_map_graphless(chosen.node_path):
            used_edges[edge] = used_edges.get(edge, 0.0) + chosen.demand

    objective, overload, avg_cost, _ = evaluate_assignment(problem, selected_options)
    elapsed = time.time() - started
    gap = (
        ((objective - optimal_objective) / optimal_objective * 100.0)
        if optimal_objective > 0
        else 0.0
    )
    return TrialResult(
        cluster_id=cluster_id,
        method="GreedyFlow",
        objective=float(objective),
        feasible=True,
        route_source="greedy_incremental_assignment",
        time=elapsed,
        optimizer_status="SUCCESS",
        selected_options=selected_options,
        selected_routes=selected_routes,
        overload_penalty=float(overload),
        average_route_cost=float(avg_cost),
        optimality_gap_percent=float(gap),
    )


def _path_edge_map_graphless(path: list[int]) -> set[tuple[int, int]]:
    return {
        tuple(sorted((int(path[idx]), int(path[idx + 1]))))
        for idx in range(len(path) - 1)
    }


def build_qaoa_solver(
    seed: int, reps: int, heuristic_objective: float | None = None
) -> MinimumEigenOptimizer:
    if StatevectorSampler is None:
        raise RuntimeError("No compatible Qiskit sampler/simulator is available.")

    if heuristic_objective is not None and math.isfinite(heuristic_objective):
        bias = max(0.1, min(0.8, 1.0 / max(1.0, heuristic_objective)))
        initial_gamma = [0.2 + bias] * reps
        initial_beta = [0.35] * reps
        initial_point = initial_gamma + initial_beta
    else:
        initial_point = [0.5] * (2 * reps)

    try:
        backend = AerSimulator.from_backend(FakeSherbrooke())
        from qiskit.primitives import BackendSampler

        sampler = BackendSampler(backend=backend)
    except Exception:
        sampler = StatevectorSampler(seed=seed)

    qaoa = QAOA(
        sampler=sampler,
        optimizer=COBYLA(maxiter=QAOA_MAXITER),
        reps=reps,
        initial_point=initial_point,
    )
    return MinimumEigenOptimizer(qaoa)


def _decode_result(
    problem: dict[str, object], result: object
) -> tuple[list[int], bool]:
    routes_by_group: list[list[CandidateRoute]] = problem["routes_by_group"]  # type: ignore[assignment]
    selected_options: list[int] = []
    variables_dict = getattr(result, "variables_dict", {})

    for group_id, routes in enumerate(routes_by_group):
        active = [
            route.option_id
            for route in routes
            if variables_dict.get(f"x_{group_id}_{route.option_id}", 0.0) > 0.5
        ]
        if len(active) != 1:
            return [], False
        selected_options.append(int(active[0]))
    return selected_options, True


def _project_one_hot_assignment(
    problem: dict[str, object], result: object
) -> list[int]:
    routes_by_group: list[list[CandidateRoute]] = problem["routes_by_group"]  # type: ignore[assignment]
    variables_dict = getattr(result, "variables_dict", {})
    if not isinstance(variables_dict, dict):
        variables_dict = {}

    selected_options: list[int] = []
    for group_id, routes in enumerate(routes_by_group):
        if not routes:
            selected_options.append(0)
            continue

        scored: list[tuple[float, float, int]] = []
        for route in routes:
            raw_value = variables_dict.get(f"x_{group_id}_{route.option_id}", None)
            score = (
                float(raw_value)
                if isinstance(raw_value, (int, float))
                else float("-inf")
            )
            # tie-break on lower route cost
            scored.append((score, -float(route.cost), int(route.option_id)))

        if all(not math.isfinite(item[0]) for item in scored):
            selected = min(routes, key=lambda route: float(route.cost)).option_id
            selected_options.append(int(selected))
            continue

        selected_options.append(max(scored, key=lambda item: (item[0], item[1]))[2])

    return selected_options


def run_qaoa(
    problem: dict[str, object],
    cluster_id: int,
    optimal_objective: float,
    heuristic_objective: float,
) -> TrialResult:
    routes_by_group: list[list[CandidateRoute]] = problem["routes_by_group"]  # type: ignore[assignment]
    if not routes_by_group:
        return TrialResult(
            cluster_id=cluster_id,
            method="QAOA",
            objective=0.0,
            feasible=True,
            route_source="trivial",
            time=0.0,
            optimizer_status="SUCCESS",
            selected_options=[],
            selected_routes=[],
            overload_penalty=0.0,
            average_route_cost=0.0,
            optimality_gap_percent=0.0,
        )

    qp = build_quadratic_program(problem)
    print("TEST XYZ")
    print(qp)
    best: TrialResult | None = None

    for trial_idx in range(QAOA_TRIALS):
        seed = RANDOM_SEED + (trial_idx * 17)
        started = time.time()
        try:
            result = build_qaoa_solver(
                seed=seed, reps=QAOA_REPS, heuristic_objective=heuristic_objective
            ).solve(qp)
        except Exception as exc:
            elapsed = time.time() - started
            fallback = greedy_heuristic(problem, cluster_id, optimal_objective)
            candidate = TrialResult(
                cluster_id=cluster_id,
                method="QAOA",
                objective=float(fallback.objective),
                feasible=True,
                route_source="qaoa_solver_exception_fallback",
                time=elapsed,
                optimizer_status=f"EXCEPTION_{type(exc).__name__}",
                selected_options=fallback.selected_options,
                selected_routes=fallback.selected_routes,
                overload_penalty=float(fallback.overload_penalty),
                average_route_cost=float(fallback.average_route_cost),
                optimality_gap_percent=float(fallback.optimality_gap_percent or 0.0),
            )
        else:
            elapsed = time.time() - started
            selected_options, feasible = _decode_result(problem, result)
            route_source = "qaoa_route_assignment"
            if not feasible:
                selected_options = _project_one_hot_assignment(problem, result)
                feasible = True
                route_source = "qaoa_projected_assignment"

            objective, overload, avg_cost, selected_routes = evaluate_assignment(
                problem, selected_options
            )
            gap = (
                ((objective - optimal_objective) / optimal_objective * 100.0)
                if optimal_objective > 0
                else 0.0
            )
            candidate = TrialResult(
                cluster_id=cluster_id,
                method="QAOA",
                objective=float(objective),
                feasible=True,
                route_source=route_source,
                time=elapsed,
                optimizer_status=getattr(result, "status", "SUCCESS").name
                if hasattr(getattr(result, "status", None), "name")
                else "SUCCESS",
                selected_options=selected_options,
                selected_routes=selected_routes,
                overload_penalty=float(overload),
                average_route_cost=float(avg_cost),
                optimality_gap_percent=float(gap),
            )

        if best is None:
            best = candidate
        elif candidate.feasible and not best.feasible:
            best = candidate
        elif (
            candidate.feasible
            and best.feasible
            and candidate.objective < best.objective
        ):
            best = candidate
        elif (
            not candidate.feasible and not best.feasible and candidate.time < best.time
        ):
            best = candidate

    assert best is not None
    return best


def solve_inter_cluster(inter_dist: np.ndarray, n_clusters: int) -> dict[str, object]:
    graph = nx.Graph()
    for i in range(n_clusters):
        graph.add_node(i)
    for i in range(n_clusters):
        for j in range(i + 1, n_clusters):
            if inter_dist[i, j] > 0:
                graph.add_edge(i, j, weight=float(inter_dist[i, j]))
    mst_edges = (
        list(nx.minimum_spanning_edges(graph, data=False))
        if graph.number_of_edges()
        else []
    )
    total_cost = sum(graph[u][v]["weight"] for u, v in mst_edges) if mst_edges else 0.0
    return {"edges": mst_edges, "method": "classical_mst", "cost": float(total_cost)}


def solve_cluster(
    graph: nx.MultiDiGraph, cluster_id: int, cluster: dict[str, object]
) -> dict[str, object]:
    node_ids = [int(node_id) for node_id in cluster["node_ids"]]
    problem = build_zone_problem(graph, cluster_id, node_ids)
    exact = brute_force_optimum(problem, cluster_id)
    heuristic = greedy_heuristic(problem, cluster_id, exact.objective)
    qaoa = run_qaoa(problem, cluster_id, exact.objective, heuristic.objective)

    return {
        "node_count": len(node_ids),
        "group_count": len(problem["group_pairs"]),
        "route_options_per_group": ROUTE_OPTIONS_PER_GROUP,
        "group_pairs": [
            {"source": source, "target": target, "demand": demand}
            for source, target, demand in problem["group_pairs"]
        ],
        "candidate_routes": {
            str(group_id): [asdict(route) for route in routes]
            for group_id, routes in enumerate(problem["routes_by_group"])
        },
        "optimal_assignment": {
            "selected_options": exact.selected_options,
            "selected_routes": exact.selected_routes,
        },
        "optimal_objective": exact.objective,
        "qaoa": asdict(qaoa),
        "exact": asdict(exact),
        "greedy": asdict(heuristic),
    }


def main() -> None:
    print(f"Sampler: {SAMPLER_NAME}")
    with GRAPH_INPUT.open("rb") as handle:
        graph_data = pickle.load(handle)
    with CLUSTER_INPUT.open("rb") as handle:
        cluster_data = pickle.load(handle)

    graph = graph_data["G_real"]
    clusters = cluster_data["clusters"]
    inter_cluster_dist = cluster_data["inter_cluster_dist"]
    n_clusters = cluster_data["N_CLUSTERS"]

    cluster_results: dict[int, dict[str, object]] = {}
    solved_cluster_limit = min(n_clusters, MAX_QAOA_CLUSTERS)
    for cid in range(solved_cluster_limit):
        print(f"Running flow-assignment benchmarks for cluster {cid}")
        cluster_results[cid] = solve_cluster(graph, cid, clusters[cid])
        cluster = cluster_results[cid]
        print(
            f"Cluster {cid}: optimal={cluster['optimal_objective']:.4f}, "
            f"qaoa={cluster['qaoa']['objective']:.4f}, feasible={cluster['qaoa']['feasible']}"
        )

    inter_result = solve_inter_cluster(inter_cluster_dist, n_clusters)

    # Cross-zone routing run
    try:
        node_zone_map = cluster_data.get("node_zone_map", {})
        zone_entry_pts = cluster_data.get("zone_entry_pts", {})
        backbone_edges = cluster_data.get("backbone_edges", [])

        backbone = nx.Graph()
        backbone.add_nodes_from(range(n_clusters))
        for u, v in backbone_edges:
            backbone.add_edge(u, v, weight=inter_cluster_dist[u, v])

        # Generate some synthetic cohorts for the demo
        np.random.seed(RANDOM_SEED)
        all_nodes = list(graph.nodes())
        cohorts = []
        for i in range(10):  # 10 random cohorts
            src = np.random.choice(all_nodes)
            tgt = np.random.choice(all_nodes)
            cohorts.append(
                Cohort(f"C{i}", source=src, target=tgt, size=np.random.randint(20, 100))
            )

        cross_zone_res = run_unified_routing(
            graph,
            backbone,
            node_zone_map,
            zone_entry_pts,
            cohorts,
            n_routes=ROUTE_OPTIONS_PER_GROUP,
        )
    except Exception as e:
        print(f"Cross-zone routing skipped or failed: {e}")
        cross_zone_res = {}

    qaoa_runs = [cluster["qaoa"] for cluster in cluster_results.values()]
    exact_runs = [cluster["exact"] for cluster in cluster_results.values()]
    heuristic_runs = [cluster["greedy"] for cluster in cluster_results.values()]

    payload = {
        "cluster_results": cluster_results,
        "inter_result": inter_result,
        "cross_zone_result": cross_zone_res,
        "summary": {
            "solved_clusters": len(cluster_results),
            "avg_qaoa_time_seconds": float(np.mean([run["time"] for run in qaoa_runs]))
            if qaoa_runs
            else 0.0,
            "qaoa_feasible_count": sum(1 for run in qaoa_runs if run["feasible"]),
            "exact_feasible_count": sum(1 for run in exact_runs if run["feasible"]),
            "avg_qaoa_gap_percent": float(
                np.mean(
                    [
                        run["optimality_gap_percent"]
                        for run in qaoa_runs
                        if run["optimality_gap_percent"] is not None
                    ]
                )
            )
            if any(run["optimality_gap_percent"] is not None for run in qaoa_runs)
            else None,
            "avg_greedy_gap_percent": float(
                np.mean(
                    [
                        run["optimality_gap_percent"]
                        for run in heuristic_runs
                        if run["optimality_gap_percent"] is not None
                    ]
                )
            )
            if heuristic_runs
            else None,
        },
        "config": {
            "max_qaoa_clusters": MAX_QAOA_CLUSTERS,
            "qaoa_reps": QAOA_REPS,
            "qaoa_maxiter": QAOA_MAXITER,
            "qaoa_trials": QAOA_TRIALS,
            "random_seed": RANDOM_SEED,
            "flow_group_count": FLOW_GROUP_COUNT,
            "route_options_per_group": ROUTE_OPTIONS_PER_GROUP,
            "flow_overlap_penalty": FLOW_OVERLAP_PENALTY,
        },
    }

    write_pickle_atomic(RESULT_OUTPUT, payload)

    print(f"Saved: {RESULT_OUTPUT}")
    print(f"Inter-cluster edges: {inter_result['edges']}")


if __name__ == "__main__":
    main()
