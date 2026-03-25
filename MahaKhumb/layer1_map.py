"""Goal 2: fetch or synthesize a weighted Prayagraj network."""

from __future__ import annotations

import pickle
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import osmnx as ox

from config import (
    FORCE_SYNTHETIC_GRAPH,
    GRAPH_IMAGE_OUTPUT,
    GRAPH_OUTPUT,
    RADIUS_METERS,
    RANDOM_SEED,
    SANGAM_LAT,
    SANGAM_LON,
    SYNTHETIC_GRID_SIDE,
)
from stgnn_predictor import forecast_node_densities, persist_predictive_state

OUTPUT_GRAPH = GRAPH_OUTPUT
OUTPUT_IMAGE = GRAPH_IMAGE_OUTPUT
RNG = np.random.default_rng(RANDOM_SEED)


def _synthesise_graph() -> tuple[nx.MultiDiGraph, object, object]:
    base = nx.grid_2d_graph(SYNTHETIC_GRID_SIDE, SYNTHETIC_GRID_SIDE)
    base = nx.convert_node_labels_to_integers(base, ordering="sorted")
    directed = nx.MultiDiGraph()
    directed.graph["crs"] = "EPSG:4326"

    side = SYNTHETIC_GRID_SIDE
    for node in base.nodes():
        row, col = divmod(node, side)
        x = SANGAM_LON + (col - side / 2) * 0.0015
        y = SANGAM_LAT + (row - side / 2) * 0.0015
        directed.add_node(node, x=x, y=y)

    for u, v in base.edges():
        length = float(RNG.uniform(50, 250))
        for src, dst in ((u, v), (v, u)):
            directed.add_edge(src, dst, length=length, travel_time=length / 1.2)

    nodes_gdf, edges_gdf = ox.convert.graph_to_gdfs(directed)
    return directed, nodes_gdf, edges_gdf


def _download_graph() -> tuple[nx.MultiDiGraph, object, object]:
    ox.settings.use_cache = True
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            category=FutureWarning,
            module="osmnx",
        )
        warnings.filterwarnings(
            "ignore",
            category=UserWarning,
            module="osmnx",
        )
        graph = ox.graph.graph_from_point(
            (SANGAM_LAT, SANGAM_LON),
            dist=RADIUS_METERS,
            network_type="walk",
        )
        try:
            graph = ox.routing.add_edge_speeds(graph)
            graph = ox.routing.add_edge_travel_times(graph)
        except Exception:
            for _, _, _, data in graph.edges(keys=True, data=True):
                length = float(data.get("length", 100.0))
                data["travel_time"] = float(data.get("travel_time", length / 1.2))

    nodes_gdf, edges_gdf = ox.convert.graph_to_gdfs(graph)
    return graph, nodes_gdf, edges_gdf


def add_weights(graph: nx.MultiDiGraph) -> None:
    import math
    for _, _, _, data in graph.edges(keys=True, data=True):
        road_length = float(data.get("length", 100.0))
        # Base desired walking velocity (v0)
        v_0 = 1.3  # m/s
        
        # Simulate extreme localized crowd density (pedestrians per square meter)
        # In a real environment, this would stream from STGNN predictions or CCTV.
        density = float(RNG.uniform(0.1, 8.0))
        
        # Non-Linear Congestion Penalty (Social Force Model integration)
        # Velocity decays rapidly as physical spacing approaches the critical threshold ~4.0 p/sqm
        critical_density = 4.0
        if density > critical_density:
            v_actual = v_0 * math.exp(-(density - critical_density) / 1.1)
        else:
            v_actual = v_0 - (density * 0.1)
            
        # Prevent division by zero if completely clogged ("faster-is-slower" effect)
        v_actual = max(0.05, v_actual)
        
        # SFM mathematically accurate travel time
        dynamic_travel_time = road_length / v_actual
        
        data["simulated_density"] = density
        data["w_congestion"] = density / 8.0
        data["w_safety"] = float(max(0.1, 1.0 - (road_length / 500.0)))
        data["w_time"] = dynamic_travel_time
        
        # Macro aggregation of SFM repulsions into QUBO-friendly edge weights
        alpha, beta, gamma = 0.5, 0.3, 0.2
        data["combined_weight"] = (
            alpha * data["w_congestion"]
            + beta * data["w_safety"]
            + gamma * (data["w_time"] / 300.0)
        )


def apply_predictive_weights(graph: nx.MultiDiGraph) -> dict[str, object]:
    import math

    forecast_by_node, summary = forecast_node_densities(graph)

    for u, v, _, data in graph.edges(keys=True, data=True):
        predicted_density = (
            float(forecast_by_node.get(int(u), data.get("simulated_density", 0.5)))
            + float(forecast_by_node.get(int(v), data.get("simulated_density", 0.5)))
        ) / 2.0

        road_length = float(data.get("length", 100.0))
        v_0 = 1.3
        critical_density = 4.0
        if predicted_density > critical_density:
            predicted_velocity = v_0 * math.exp(-(predicted_density - critical_density) / 1.1)
        else:
            predicted_velocity = v_0 - (predicted_density * 0.1)
        predicted_velocity = max(0.05, predicted_velocity)
        predicted_time = road_length / predicted_velocity
        predicted_congestion = predicted_density / 8.0
        predicted_safety = float(max(0.1, 1.0 - (road_length / 500.0)))

        alpha, beta, gamma = 0.5, 0.3, 0.2
        predicted_weight = (
            alpha * predicted_congestion
            + beta * predicted_safety
            + gamma * (predicted_time / 300.0)
        )

        data["predicted_density"] = predicted_density
        data["predicted_travel_time"] = predicted_time
        data["predicted_combined_weight"] = predicted_weight
        data["combined_weight_static"] = data["combined_weight"]
        data["combined_weight"] = predicted_weight

    persist_predictive_state(forecast_by_node, summary)
    return {
        "backend": summary.backend,
        "history_steps": summary.history_steps,
        "training_loss": summary.training_loss,
        "forecast_mean_density": summary.forecast_mean_density,
        "forecast_peak_density": summary.forecast_peak_density,
    }


def save_outputs(graph: nx.MultiDiGraph, nodes_gdf: object, edges_gdf: object) -> None:
    with OUTPUT_GRAPH.open("wb") as handle:
        pickle.dump(
            {
                "G_real": graph,
                "nodes_gdf": nodes_gdf,
                "edges_gdf": edges_gdf,
                "metadata": {
                    "center": {"lat": SANGAM_LAT, "lon": SANGAM_LON},
                    "radius_meters": RADIUS_METERS,
                    "node_count": len(nodes_gdf),
                    "edge_count": len(edges_gdf),
                    "predictive_summary": graph.graph.get("predictive_summary", {}),
                },
            },
            handle,
        )

    fig, ax = ox.plot.plot_graph(
        graph,
        node_size=3,
        edge_linewidth=0.5,
        bgcolor="white",
        show=False,
        close=False,
    )
    ax.set_title("Real Walkable Network - Kumbh Mela Area (Prayagraj)", fontsize=14)
    fig.savefig(OUTPUT_IMAGE, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    source = "osm"
    if FORCE_SYNTHETIC_GRAPH:
        print("Map mode: synthetic fallback forced by MAHAKHUMB_FORCE_SYNTHETIC=1")
        graph, nodes_gdf, edges_gdf = _synthesise_graph()
        source = "synthetic"
    else:
        print("Map mode: attempting OpenStreetMap download")
        try:
            graph, nodes_gdf, edges_gdf = _download_graph()
        except Exception as exc:
            print(f"Map mode: OpenStreetMap unavailable, switching to synthetic fallback")
            print(f"Fallback reason: {type(exc).__name__}: {exc}")
            graph, nodes_gdf, edges_gdf = _synthesise_graph()
            source = "synthetic"

    add_weights(graph)
    predictive_summary = apply_predictive_weights(graph)
    graph.graph["source"] = source
    graph.graph["center_lat"] = SANGAM_LAT
    graph.graph["center_lon"] = SANGAM_LON
    graph.graph["radius_meters"] = RADIUS_METERS
    graph.graph["predictive_summary"] = predictive_summary
    save_outputs(graph, nodes_gdf, edges_gdf)
    print(f"Graph source: {source}")
    print(f"Nodes: {len(nodes_gdf)}")
    print(f"Edges: {len(edges_gdf)}")
    print(f"Predictive backend: {predictive_summary['backend']}")
    print(f"Saved: {OUTPUT_GRAPH}")
    print(f"Saved: {OUTPUT_IMAGE}")


if __name__ == "__main__":
    main()
