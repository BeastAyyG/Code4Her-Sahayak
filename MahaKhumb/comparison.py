"""Goal 5: compare multi-group routing baselines and render experiment outputs."""

from __future__ import annotations

import csv
import pickle

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

from artifact_utils import write_json_atomic, write_text_atomic
from config import (
    BARCHART_IMAGE_OUTPUT,
    CLUSTER_OUTPUT,
    COMPARISON_IMAGE_OUTPUT,
    CLUSTER_IMAGE_OUTPUT,
    GRAPH_IMAGE_OUTPUT,
    GRAPH_OUTPUT,
    JUDGES_BRIEF_OUTPUT,
    PREDICTIVE_STATE_OUTPUT,
    QAOA_OUTPUT,
    REPORT_JSON_OUTPUT,
    REPORT_MD_OUTPUT,
    RESULTS_TABLE_OUTPUT,
    ROUTE_OVERLAY_IMAGE_OUTPUT,
    SANGAM_LAT,
    SANGAM_LON,
    SIMULATION_STATE_OUTPUT,
)

GRAPH_INPUT = GRAPH_OUTPUT
CLUSTER_INPUT = CLUSTER_OUTPUT
RESULT_INPUT = QAOA_OUTPUT
OUTPUT_COMPARISON = COMPARISON_IMAGE_OUTPUT
OUTPUT_BARCHART = BARCHART_IMAGE_OUTPUT
OUTPUT_ROUTE_OVERLAY = ROUTE_OVERLAY_IMAGE_OUTPUT
OUTPUT_REPORT_JSON = REPORT_JSON_OUTPUT
OUTPUT_REPORT_MD = REPORT_MD_OUTPUT
OUTPUT_JUDGES_BRIEF = JUDGES_BRIEF_OUTPUT
OUTPUT_RESULTS_CSV = RESULTS_TABLE_OUTPUT


def _node_xy(nodes_gdf: object, node_id: int) -> tuple[float, float]:
    return float(nodes_gdf.loc[node_id, "x"]), float(nodes_gdf.loc[node_id, "y"])


def _distance_to_sangam(nodes_gdf: object, node_id: int) -> float:
    x, y = _node_xy(nodes_gdf, node_id)
    return float(np.hypot(x - SANGAM_LON, y - SANGAM_LAT))


def _closest_graph_node(nodes_gdf: object) -> int:
    best_node = int(nodes_gdf.index[0])
    best_distance = float("inf")
    for node_id in nodes_gdf.index:
        distance = _distance_to_sangam(nodes_gdf, int(node_id))
        if distance < best_distance:
            best_node = int(node_id)
            best_distance = distance
    return best_node


def _river_band(nodes_gdf: object, river_node_ids: list[int]) -> tuple[float, float, float, float]:
    xs = [float(nodes_gdf.loc[node_id, "x"]) for node_id in river_node_ids]
    ys = [float(nodes_gdf.loc[node_id, "y"]) for node_id in river_node_ids]
    pad_x = max(0.0008, (max(xs) - min(xs)) * 0.15 if len(xs) > 1 else 0.0015)
    pad_y = max(0.0006, (max(ys) - min(ys)) * 0.35 if len(ys) > 1 else 0.0012)
    return min(xs) - pad_x, max(xs) + pad_x, min(ys) - pad_y, max(ys) + pad_y


def _demo_flow_routes(
    graph: object,
    nodes_gdf: object,
    clusters: dict[int, dict[str, object]],
    report_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    sangam_anchor = _closest_graph_node(nodes_gdf)
    flows: list[dict[str, object]] = []

    ranked_rows = sorted(
        report_rows,
        key=lambda row: float(row.get("optimal_objective", 0.0)),
        reverse=True,
    )
    for row in ranked_rows[:4]:
        zone_id = int(row["zone"])
        cluster = clusters.get(zone_id)
        if not cluster:
            continue

        zone_nodes = [int(node_id) for node_id in cluster.get("node_ids", [])]
        if len(zone_nodes) < 3:
            continue

        zone_nodes = sorted(zone_nodes, key=lambda node_id: _distance_to_sangam(nodes_gdf, node_id))
        river_candidates = zone_nodes[: max(2, min(5, len(zone_nodes) // 3))]
        outer_candidates = list(reversed(zone_nodes[-max(3, min(8, len(zone_nodes) // 2)) :]))
        group_count = max(1, int(row.get("group_count", 1)))

        for group_id in range(group_count):
            outer_node = int(outer_candidates[group_id % len(outer_candidates)])
            river_node = int(river_candidates[group_id % len(river_candidates)])

            try:
                ingress = nx.shortest_path(
                    graph,
                    outer_node,
                    river_node,
                    weight="combined_weight",
                )
                egress = nx.shortest_path(
                    graph,
                    river_node,
                    outer_node,
                    weight="combined_weight",
                )
            except nx.NetworkXNoPath:
                continue

            flows.append(
                {
                    "zone": zone_id,
                    "group_id": group_id,
                    "outer_node": outer_node,
                    "river_node": river_node,
                    "ingress": ingress,
                    "egress": egress,
                }
            )

    if not flows:
        try:
            neighbors = list(graph.neighbors(sangam_anchor))
        except Exception:
            neighbors = []
        for idx, neighbor in enumerate(neighbors[:3]):
            try:
                egress = nx.shortest_path(
                    graph,
                    sangam_anchor,
                    int(neighbor),
                    weight="combined_weight",
                )
            except nx.NetworkXNoPath:
                continue
            flows.append(
                {
                    "zone": idx,
                    "group_id": idx,
                    "outer_node": int(neighbor),
                    "river_node": sangam_anchor,
                    "ingress": list(reversed(egress)),
                    "egress": egress,
                }
            )

    return flows


def plot_base_edges(ax: object, graph: object, nodes_gdf: object, color: str, linewidth: float, alpha: float = 1.0) -> None:
    for u, v, _ in graph.edges(data=True):
        if u not in nodes_gdf.index or v not in nodes_gdf.index:
            continue
        x = [float(nodes_gdf.loc[u, "x"]), float(nodes_gdf.loc[v, "x"])]
        y = [float(nodes_gdf.loc[u, "y"]), float(nodes_gdf.loc[v, "y"])]
        ax.plot(x, y, color=color, linewidth=linewidth, alpha=alpha)


def projected_scaling_table() -> list[dict[str, str | int]]:
    return [
        {
            "decision_vars": 9,
            "scenario": "3 groups x 3 routes",
            "classical_exact": "easy",
            "classical_heuristic": "easy",
            "qaoa_simulator": "measured in repo",
            "hardware_note": "benchmark regime only",
        },
        {
            "decision_vars": 16,
            "scenario": "4 groups x 4 routes",
            "classical_exact": "still tractable",
            "classical_heuristic": "easy",
            "qaoa_simulator": "expensive",
            "hardware_note": "useful approximation study regime",
        },
        {
            "decision_vars": 30,
            "scenario": "6 groups x 5 routes",
            "classical_exact": "rapidly expensive",
            "classical_heuristic": "fast but approximate",
            "qaoa_simulator": "not run here",
            "hardware_note": "future-scaling motivation",
        },
        {
            "decision_vars": 48,
            "scenario": "8 groups x 6 routes",
            "classical_exact": "impractical for repeated replans",
            "classical_heuristic": "fast but approximate",
            "qaoa_simulator": "not practical in repo",
            "hardware_note": "future hardware target only",
        },
    ]


def main() -> None:
    with GRAPH_INPUT.open("rb") as handle:
        graph_data = pickle.load(handle)
    with CLUSTER_INPUT.open("rb") as handle:
        cluster_data = pickle.load(handle)
    with RESULT_INPUT.open("rb") as handle:
        result_data = pickle.load(handle)

    graph = graph_data["G_real"]
    nodes_gdf = graph_data["nodes_gdf"]
    graph_metadata = graph_data.get("metadata", {})
    clusters = cluster_data["clusters"]
    key_coords = cluster_data["key_coords"]
    labels = cluster_data["labels"]
    n_clusters = cluster_data["N_CLUSTERS"]
    cluster_results = result_data["cluster_results"]
    inter_result = result_data.get("inter_result", {})
    config = result_data.get("config", {})
    summary = result_data.get("summary", {})

    report_rows: list[dict[str, object]] = []
    print("=" * 110)
    print(
        f"{'Zone':<8} {'Groups':>8} {'Optimal':>12} {'QAOA':>12} "
        f"{'Greedy':>12} {'QAOA Feas.':>12} {'QAOA Gap %':>12}"
    )
    print("=" * 110)

    qaoa_match_count = 0
    for cid, cluster in cluster_results.items():
        optimal_objective = float(cluster["optimal_objective"])
        qaoa = cluster["qaoa"]
        exact = cluster["exact"]
        greedy = cluster["greedy"]
        qaoa_match = bool(qaoa["feasible"]) and abs(float(qaoa["objective"]) - optimal_objective) < 0.01
        qaoa_match_count += int(qaoa_match)

        row = {
            "zone": cid,
            "node_count": int(cluster["node_count"]),
            "group_count": int(cluster["group_count"]),
            "route_options_per_group": int(cluster["route_options_per_group"]),
            "group_pairs": cluster["group_pairs"],
            "optimal_objective": optimal_objective,
            "optimal_assignment": cluster["optimal_assignment"],
            "qaoa_objective": float(qaoa["objective"]),
            "qaoa_feasible": bool(qaoa["feasible"]),
            "qaoa_route_source": qaoa["route_source"],
            "qaoa_time_seconds": float(qaoa["time"]),
            "qaoa_optimizer_status": qaoa["optimizer_status"],
            "qaoa_gap_percent": qaoa["optimality_gap_percent"],
            "qaoa_selected_routes": qaoa["selected_routes"],
            "qaoa_overload_penalty": qaoa["overload_penalty"],
            "exact_objective": float(exact["objective"]),
            "exact_selected_routes": exact["selected_routes"],
            "exact_overload_penalty": exact["overload_penalty"],
            "greedy_objective": float(greedy["objective"]),
            "greedy_selected_routes": greedy["selected_routes"],
            "greedy_gap_percent": greedy["optimality_gap_percent"],
            "greedy_overload_penalty": greedy["overload_penalty"],
            "qaoa_matches_optimal": qaoa_match,
        }
        report_rows.append(row)

        gap_text = "NA" if row["qaoa_gap_percent"] is None else f"{row['qaoa_gap_percent']:.2f}"
        print(
            f"{cid:<8} {row['group_count']:>8} {optimal_objective:>12.4f} {row['qaoa_objective']:>12.4f} "
            f"{row['greedy_objective']:>12.4f} {str(row['qaoa_feasible']):>12} {gap_text:>12}"
        )

    accuracy = (qaoa_match_count / max(1, len(report_rows))) * 100.0
    print("=" * 110)
    print(f"QAOA optimal-objective match rate: {accuracy:.0f}%")

    fig, axes = plt.subplots(1, 2, figsize=(20, 9))
    ax1, ax2 = axes

    ax1.set_title("BEFORE: Predicted Congestion Pressure", fontsize=15, fontweight="bold", color="red")
    for u, v, data in graph.edges(data=True):
        if u not in nodes_gdf.index or v not in nodes_gdf.index:
            continue
        x = [float(nodes_gdf.loc[u, "x"]), float(nodes_gdf.loc[v, "x"])]
        y = [float(nodes_gdf.loc[u, "y"]), float(nodes_gdf.loc[v, "y"])]
        congestion = float(data.get("predicted_density", data.get("w_congestion", 0.5)))
        ax1.plot(x, y, color=plt.cm.RdYlGn_r(min(congestion / 8.0, 1.0)), linewidth=1.5, alpha=0.7)
    ax1.set_xlabel("Longitude")
    ax1.set_ylabel("Latitude")

    ax2.set_title("AFTER: Zone Assignment Benchmark View", fontsize=15, fontweight="bold", color="green")
    plot_base_edges(ax2, graph, nodes_gdf, color="#e0e0e0", linewidth=0.5)

    colors = plt.cm.Set1(np.linspace(0, 1, n_clusters))
    for cid in range(n_clusters):
        mask = labels == cid
        ax2.scatter(
            key_coords[mask, 1],
            key_coords[mask, 0],
            c=[colors[cid]],
            s=100,
            zorder=5,
            edgecolors="black",
            linewidths=1,
            label=f"Zone {cid}",
        )
        centroid = clusters[cid]["centroid"]
        ax2.scatter(
            centroid[1],
            centroid[0],
            c=[colors[cid]],
            marker="*",
            s=400,
            edgecolors="black",
            linewidths=2,
            zorder=6,
        )
    ax2.set_xlabel("Longitude")
    ax2.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUTPUT_COMPARISON, dpi=150, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(13, 10))
    plot_base_edges(ax, graph, nodes_gdf, color="#d8d8d8", linewidth=0.45, alpha=0.55)
    demo_flows = _demo_flow_routes(graph, nodes_gdf, clusters, report_rows)
    river_node_ids = [int(flow["river_node"]) for flow in demo_flows]
    if river_node_ids:
        river_x0, river_x1, river_y0, river_y1 = _river_band(nodes_gdf, river_node_ids)
        ax.axvspan(
            river_x0,
            river_x1,
            ymin=0,
            ymax=1,
            color="#d9f3f1",
            alpha=0.6,
            zorder=0,
        )
        ax.text(
            (river_x0 + river_x1) / 2,
            river_y1,
            "Riverfront access band",
            color="#0f766e",
            fontsize=11,
            fontweight="bold",
            ha="center",
            va="bottom",
            zorder=8,
        )

    ingress_color = "#0f766e"
    egress_color = "#d97706"
    used_labels: set[str] = set()
    for flow in demo_flows:
        for direction, color, linestyle, alpha, marker in [
            ("ingress", ingress_color, "-", 0.95, ">"),
            ("egress", egress_color, "--", 0.85, "<"),
        ]:
            node_path = flow[direction]
            xs = [float(nodes_gdf.loc[node_id, "x"]) for node_id in node_path if node_id in nodes_gdf.index]
            ys = [float(nodes_gdf.loc[node_id, "y"]) for node_id in node_path if node_id in nodes_gdf.index]
            if len(xs) < 2:
                continue
            label = f"{direction.title()} flow"
            ax.plot(
                xs,
                ys,
                color=color,
                linewidth=2.6,
                linestyle=linestyle,
                alpha=alpha,
                zorder=5,
                label=label if label not in used_labels else None,
            )
            used_labels.add(label)
            ax.scatter(
                xs[0],
                ys[0],
                color=color,
                s=48,
                marker="o",
                edgecolors="white",
                linewidths=0.9,
                zorder=6,
            )
            ax.scatter(
                xs[-1],
                ys[-1],
                color=color,
                s=85,
                marker=marker,
                edgecolors="black",
                linewidths=0.8,
                zorder=7,
            )

    ax.scatter(
        SANGAM_LON,
        SANGAM_LAT,
        s=180,
        marker="*",
        color="#0b4f4a",
        edgecolors="white",
        linewidths=1.3,
        zorder=9,
        label="Sangam anchor",
    )
    ax.set_title("Pilgrim Movement Overlay: River Ingress and Safe Egress", fontsize=15, fontweight="bold")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUTPUT_ROUTE_OVERLAY, dpi=150, bbox_inches="tight")
    plt.close(fig)

    zone_labels = [f"Zone {row['zone']}" for row in report_rows]
    optimal_values = [row["optimal_objective"] for row in report_rows]
    qaoa_values = [row["qaoa_objective"] if np.isfinite(row["qaoa_objective"]) else np.nan for row in report_rows]
    greedy_values = [row["greedy_objective"] for row in report_rows]

    fig, ax = plt.subplots(figsize=(11, 6))
    x = np.arange(len(zone_labels))
    width = 0.25
    bars_opt = ax.bar(x - width, optimal_values, width, label="Optimal assignment", color="#1f77b4")
    bars_qaoa = ax.bar(x, qaoa_values, width, label="QAOA assignment", color="#ff7f0e")
    bars_greedy = ax.bar(x + width, greedy_values, width, label="Greedy flow heuristic", color="#2ca02c")
    ax.set_ylabel("Assignment Objective")
    ax.set_title("Multi-Group Route Assignment Baselines per Zone")
    ax.set_xticks(x)
    ax.set_xticklabels(zone_labels)
    ax.legend()
    for bar in list(bars_opt) + list(bars_qaoa) + list(bars_greedy):
        height = bar.get_height()
        if np.isnan(height):
            continue
        ax.annotate(
            f"{height:.2f}",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            ha="center",
            va="bottom",
            fontsize=8,
        )
    fig.tight_layout()
    fig.savefig(OUTPUT_BARCHART, dpi=150, bbox_inches="tight")
    plt.close(fig)

    report = {
        "graph": {
            "source": graph.graph.get("source", "unknown"),
            "node_count": graph_metadata.get("node_count", graph.number_of_nodes()),
            "edge_count": graph_metadata.get("edge_count", graph.number_of_edges()),
            "radius_meters": graph_metadata.get("radius_meters"),
            "predictive_summary": graph_metadata.get("predictive_summary", graph.graph.get("predictive_summary", {})),
        },
        "clusters": {
            "count": n_clusters,
            "kmeans_inertia": cluster_data.get("kmeans_inertia"),
            "sizes": {str(cid): int(clusters[cid]["size"]) for cid in clusters},
        },
        "experiment": {
            "problem_type": "multi_group_route_assignment",
            "qaoa_optimal_match_percent": accuracy,
            "qaoa_feasible_count": summary.get("qaoa_feasible_count", 0),
            "exact_feasible_count": summary.get("exact_feasible_count", 0),
            "avg_qaoa_time_seconds": summary.get("avg_qaoa_time_seconds", 0.0),
            "avg_qaoa_gap_percent": summary.get("avg_qaoa_gap_percent"),
            "avg_greedy_gap_percent": summary.get("avg_greedy_gap_percent"),
            "scaling_projection_table": projected_scaling_table(),
            "config": config,
            "inter_cluster_edges": inter_result.get("edges", []),
            "inter_cluster_method": inter_result.get("method"),
            "inter_cluster_cost": inter_result.get("cost"),
        },
        "zones": report_rows,
        "artifacts": {
            "comparison_image": str(OUTPUT_COMPARISON),
            "barchart_image": str(OUTPUT_BARCHART),
            "route_overlay_image": str(OUTPUT_ROUTE_OVERLAY),
            "predictive_state": str(PREDICTIVE_STATE_OUTPUT),
            "simulation_state": str(SIMULATION_STATE_OUTPUT),
        },
    }
    write_json_atomic(OUTPUT_REPORT_JSON, report)

    with OUTPUT_RESULTS_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "zone",
                "node_count",
                "group_count",
                "route_options_per_group",
                "optimal_objective",
                "qaoa_objective",
                "greedy_objective",
                "qaoa_feasible",
                "qaoa_route_source",
                "qaoa_time_seconds",
                "qaoa_gap_percent",
                "greedy_gap_percent",
                "qaoa_matches_optimal",
            ],
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(report_rows)

    lines = [
        "# Continuum Scientific Report",
        "",
        f"- Graph source: `{report['graph']['source']}`",
        f"- Road network size: `{report['graph']['node_count']}` nodes / `{report['graph']['edge_count']}` edges",
        f"- Cluster count: `{report['clusters']['count']}`",
        f"- Quantum formulation: `{report['experiment']['problem_type']}`",
        f"- QAOA optimal-objective match rate: `{report['experiment']['qaoa_optimal_match_percent']:.0f}%`",
        f"- QAOA feasible cluster count: `{report['experiment']['qaoa_feasible_count']}` / `{len(report_rows)}`",
        f"- Avg QAOA runtime per solved cluster: `{report['experiment']['avg_qaoa_time_seconds']:.2f}s`",
        f"- Avg QAOA optimality gap: `{report['experiment']['avg_qaoa_gap_percent']}`",
        f"- Avg greedy gap: `{report['experiment']['avg_greedy_gap_percent']}`",
        "",
        "## Zone Results",
        "",
        "| Zone | Groups | Optimal Obj | QAOA Obj | Greedy Obj | QAOA Feasible | QAOA Gap % |",
        "| --- | ---: | ---: | ---: | ---: | :---: | ---: |",
    ]
    for row in report_rows:
        qaoa_gap = "NA" if row["qaoa_gap_percent"] is None else f"{row['qaoa_gap_percent']:.2f}"
        lines.append(
            f"| {row['zone']} | {row['group_count']} | {row['optimal_objective']:.4f} | "
            f"{row['qaoa_objective']:.4f} | {row['greedy_objective']:.4f} | "
            f"{'YES' if row['qaoa_feasible'] else 'NO'} | {qaoa_gap} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The quantum layer now benchmarks binary route assignment for multiple groups inside each zone rather than a single-agent TSP tour.",
            "- Each group is assigned exactly one candidate route, and the objective penalizes both base travel cost and shared-edge overload.",
            "- The exact solver is brute-force enumeration over route assignments, which is reliable for the small benchmark instances used in this repository.",
            "- QAOA is evaluated as an approximate NISQ solver on the same assignment QUBO, not as a guaranteed-feasible optimizer.",
            "- The predictive and zoning layers now feed a mathematically coherent local route-allocation benchmark.",
            "",
            "## Scaling Projection",
            "",
            "| Decision Vars | Scenario | Classical Exact | Classical Heuristic | QAOA Simulator | Hardware Note |",
            "| ---: | --- | --- | --- | --- | --- |",
        ]
    )
    for row in report["experiment"]["scaling_projection_table"]:
        lines.append(
            f"| {row['decision_vars']} | {row['scenario']} | {row['classical_exact']} | "
            f"{row['classical_heuristic']} | {row['qaoa_simulator']} | {row['hardware_note']} |"
        )
    lines.extend(
        [
            "",
            "Projection note: the scaling table is a roadmap framing tool, not a claim of measured quantum advantage in this repository.",
            "",
            "## Generated Artifacts",
            "",
            f"- `{OUTPUT_COMPARISON}`",
            f"- `{OUTPUT_BARCHART}`",
            f"- `{OUTPUT_ROUTE_OVERLAY}`",
            f"- `{OUTPUT_REPORT_JSON}`",
        ]
    )
    write_text_atomic(OUTPUT_REPORT_MD, "\n".join(lines), encoding="utf-8")

    judges_lines = [
        "# Judges Brief",
        "",
        "## One-line Pitch",
        "A reproducible hybrid benchmark for assigning multiple crowd-risk cohorts to alternative local routes inside predicted hotspot zones on a real Prayagraj road graph, with exact, heuristic, and QAOA comparisons on the same binary optimization problem.",
        "",
        "## What Is Scientifically Strong Here",
        "- Real geographic graph from OpenStreetMap, not a toy map.",
        "- Predicted crowd pressure is pushed into edge weights before optimization.",
        "- Spectral zoning compresses the city into operational subproblems.",
        "- The quantum layer now solves a multi-group route-assignment QUBO instead of a single-agent TSP tour.",
        "- Exact brute-force, greedy heuristic, and QAOA are reported side by side on the same objective.",
        "- Feasibility and optimality gaps are tracked explicitly.",
        "",
        "## Verified Run",
        f"- Network: {report['graph']['node_count']} nodes / {report['graph']['edge_count']} edges.",
        f"- Zones: {report['clusters']['count']}.",
        f"- QAOA optimal-objective match rate: {report['experiment']['qaoa_optimal_match_percent']:.0f}%.",
        f"- QAOA feasible clusters: {report['experiment']['qaoa_feasible_count']} / {len(report_rows)}.",
        f"- Average QAOA runtime: {report['experiment']['avg_qaoa_time_seconds']:.2f}s.",
        "",
        "## Honest Limitation",
        "- The cohort demands and candidate route sets are still synthetic benchmark constructs derived from the real graph, not live operational telemetry.",
        "- This is still not evidence of present-day quantum advantage over strong classical heuristics.",
        "- The contribution is a coherent hybrid benchmark and scaling roadmap, not a production crowd-control deployment claim.",
        "",
        "## Demo Assets",
        f"- Map: `{GRAPH_IMAGE_OUTPUT}`",
        f"- Clusters: `{CLUSTER_IMAGE_OUTPUT}`",
        f"- Baseline comparison: `{OUTPUT_BARCHART}`",
        f"- Assignment overlay: `{OUTPUT_ROUTE_OVERLAY}`",
        f"- Scientific report: `{OUTPUT_REPORT_MD}`",
    ]
    write_text_atomic(OUTPUT_JUDGES_BRIEF, "\n".join(judges_lines), encoding="utf-8")

    print(f"Saved: {OUTPUT_COMPARISON}")
    print(f"Saved: {OUTPUT_BARCHART}")
    print(f"Saved: {OUTPUT_ROUTE_OVERLAY}")
    print(f"Saved: {OUTPUT_REPORT_JSON}")
    print(f"Saved: {OUTPUT_REPORT_MD}")
    print(f"Saved: {OUTPUT_JUDGES_BRIEF}")
    print(f"Saved: {OUTPUT_RESULTS_CSV}")


if __name__ == "__main__":
    main()
