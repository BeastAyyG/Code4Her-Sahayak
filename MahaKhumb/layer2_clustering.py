"""Goal 3: derive cluster decomposition from the saved graph."""

from __future__ import annotations

import pickle

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from sklearn.cluster import SpectralClustering

from artifact_utils import write_pickle_atomic
from config import (
    CLUSTER_IMAGE_OUTPUT,
    CLUSTER_OUTPUT,
    GRAPH_OUTPUT,
    N_CLUSTERS,
    N_KEY_NODES,
)

GRAPH_INPUT = GRAPH_OUTPUT
IMAGE_OUTPUT = CLUSTER_IMAGE_OUTPUT


def node_xy(nodes_gdf: object, node_id: int) -> tuple[float, float]:
    row = nodes_gdf.loc[node_id]
    return float(row["y"]), float(row["x"])


def main() -> None:
    with GRAPH_INPUT.open("rb") as handle:
        data = pickle.load(handle)

    graph = data["G_real"]
    nodes_gdf = data["nodes_gdf"]

    print("Computing betweenness centrality...")
    centrality = nx.betweenness_centrality(graph, weight="combined_weight")
    top_nodes = sorted(centrality.items(), key=lambda item: item[1], reverse=True)[
        :N_KEY_NODES
    ]
    key_node_ids = [node_id for node_id, _ in top_nodes]
    key_coords = np.array(
        [node_xy(nodes_gdf, node_id) for node_id in key_node_ids], dtype=float
    )

    n_clusters = min(N_CLUSTERS, len(key_coords)) if len(key_coords) else 0
    if n_clusters < 1:
        raise RuntimeError("No key coordinates available for clustering.")

    print("Computing topology-aware distance matrix for Spectral Clustering...")
    n_nodes = len(key_node_ids)
    key_dist_matrix = np.zeros((n_nodes, n_nodes), dtype=float)
    for i in range(n_nodes):
        for j in range(i + 1, n_nodes):
            try:
                # Use actual road network travel weights, completely ignoring Euclidean physics.
                weight = nx.shortest_path_length(
                    graph,
                    key_node_ids[i],
                    key_node_ids[j],
                    weight="combined_weight",
                )
            except nx.NetworkXNoPath:
                weight = 99999.0
            key_dist_matrix[i, j] = weight
            key_dist_matrix[j, i] = weight

    # Convert exact network distances to an Affinity Matrix (exp(-gamma * D))
    gamma = (
        1.0 / np.median(key_dist_matrix[key_dist_matrix > 0])
        if np.any(key_dist_matrix > 0)
        else 1.0
    )
    affinity_matrix = np.exp(-gamma * key_dist_matrix)

    spectral = SpectralClustering(
        n_clusters=n_clusters,
        affinity="precomputed",
        random_state=42,
        assign_labels="kmeans",
    )
    labels = spectral.fit_predict(affinity_matrix)

    clusters: dict[int, dict[str, object]] = {}
    for cid in range(n_clusters):
        cluster_node_ids = [
            key_node_ids[idx] for idx, label in enumerate(labels) if label == cid
        ]
        mask = labels == cid

        # Calculate cluster centroid coordinates manually since Spectral Clustering doesn't output `.cluster_centers_`
        cluster_coords = key_coords[mask]
        centroid = (
            np.mean(cluster_coords, axis=0)
            if len(cluster_coords) > 0
            else np.array([0.0, 0.0])
        )

        clusters[cid] = {
            "node_ids": cluster_node_ids,
            "coords": cluster_coords,
            "centroid": centroid,
            "size": len(cluster_node_ids),
        }

    cluster_subgraphs: dict[int, np.ndarray] = {}
    for cid, cluster in clusters.items():
        node_ids = cluster["node_ids"]
        size = len(node_ids)
        dist_matrix = np.zeros((size, size), dtype=float)
        for i in range(size):
            for j in range(i + 1, size):
                try:
                    weight = nx.shortest_path_length(
                        graph,
                        node_ids[i],
                        node_ids[j],
                        weight="combined_weight",
                    )
                except nx.NetworkXNoPath:
                    weight = 999.0
                dist_matrix[i, j] = weight
                dist_matrix[j, i] = weight
        cluster_subgraphs[cid] = dist_matrix

    inter_cluster_dist = np.zeros((n_clusters, n_clusters), dtype=float)
    for i in range(n_clusters):
        for j in range(i + 1, n_clusters):
            ci = clusters[i]["centroid"]
            cj = clusters[j]["centroid"]
            distance = float(np.sqrt(((ci - cj) ** 2).sum()) * 111_000.0)
            inter_cluster_dist[i, j] = distance
            inter_cluster_dist[j, i] = distance

    print("Computing full node_zone_map...")
    node_zone_map = {}
    for idx, node in enumerate(key_node_ids):
        node_zone_map[node] = int(labels[idx])

    centroids = [clusters[cid]["centroid"] for cid in range(n_clusters)]
    for node in graph.nodes():
        if node not in node_zone_map:
            try:
                coords = np.array(node_xy(nodes_gdf, node))
                dists = [np.linalg.norm(coords - c) for c in centroids]
                node_zone_map[node] = int(np.argmin(dists))
            except Exception:
                node_zone_map[node] = 0

    print("Identifying zone entry points and backbone edges...")
    zone_entry_pts = {cid: set() for cid in range(n_clusters)}
    backbone_edges = set()
    for u, v in graph.edges():
        zu = node_zone_map.get(u)
        zv = node_zone_map.get(v)
        if zu is not None and zv is not None and zu != zv:
            zone_entry_pts[zu].add(u)
            zone_entry_pts[zv].add(v)
            backbone_edges.add(tuple(sorted([zu, zv])))

    zone_entry_pts_list = {k: list(v) for k, v in zone_entry_pts.items()}

    write_pickle_atomic(
        CLUSTER_OUTPUT,
        {
            "clusters": clusters,
            "cluster_subgraphs": cluster_subgraphs,
            "inter_cluster_dist": inter_cluster_dist,
            "key_node_ids": key_node_ids,
            "key_coords": key_coords,
            "labels": labels,
            "N_CLUSTERS": n_clusters,
            "node_zone_map": node_zone_map,
            "zone_entry_pts": zone_entry_pts_list,
            "backbone_edges": list(backbone_edges),
            "centrality": {node_id: float(score) for node_id, score in top_nodes},
            "kmeans_inertia": 0.0,  # Spectral doesn't produce inertia
            "config": {
                "key_node_count": N_KEY_NODES,
                "cluster_count_requested": N_CLUSTERS,
                "cluster_count_used": n_clusters,
            },
        },
    )

    colors = plt.cm.Set1(np.linspace(0, 1, n_clusters))
    fig, ax = plt.subplots(figsize=(12, 10))
    for cid in range(n_clusters):
        mask = labels == cid
        ax.scatter(
            key_coords[mask, 1],
            key_coords[mask, 0],
            c=[colors[cid]],
            s=100,
            label=f"Zone {cid} ({clusters[cid]['size']} nodes)",
            zorder=5,
            edgecolors="black",
        )
        centroid = clusters[cid]["centroid"]
        ax.scatter(
            centroid[1],
            centroid[0],
            c=[colors[cid]],
            marker="*",
            s=400,
            edgecolors="black",
            linewidths=2,
            zorder=6,
        )

    ax.set_title("Kumbh Mela - Hierarchical Zone Decomposition", fontsize=14)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.legend(loc="best", fontsize=9)
    fig.savefig(IMAGE_OUTPUT, dpi=150, bbox_inches="tight")
    plt.close(fig)

    print(f"Selected {len(key_node_ids)} key intersections")
    for cid in range(n_clusters):
        print(f"Zone {cid}: {clusters[cid]['size']} nodes")
    print(f"Saved: {CLUSTER_OUTPUT}")
    print(f"Saved: {IMAGE_OUTPUT}")


if __name__ == "__main__":
    main()
