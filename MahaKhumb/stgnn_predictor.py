"""Predictive spatiotemporal graph model for crowd-state forecasting."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import networkx as nx
import numpy as np

from config import (
    PREDICTIVE_STATE_OUTPUT,
    RANDOM_SEED,
    STGNN_EPOCHS,
    STGNN_HIDDEN_DIM,
    STGNN_HISTORY_STEPS,
    STGNN_LEARNING_RATE,
)

try:
    import torch
    from torch import nn
except ImportError:  # pragma: no cover - exercised through fallback path
    torch = None
    nn = None


@dataclass
class PredictiveSummary:
    backend: str
    node_count: int
    history_steps: int
    training_loss: float
    forecast_mean_density: float
    forecast_peak_density: float


def _node_index(graph: nx.MultiDiGraph) -> tuple[list[int], dict[int, int]]:
    node_ids = sorted(int(node_id) for node_id in graph.nodes())
    return node_ids, {node_id: idx for idx, node_id in enumerate(node_ids)}


def _normalized_adjacency(graph: nx.MultiDiGraph, node_to_idx: dict[int, int]) -> np.ndarray:
    size = len(node_to_idx)
    adjacency = np.zeros((size, size), dtype=np.float32)
    for source, target, data in graph.edges(data=True):
        src_idx = node_to_idx[int(source)]
        dst_idx = node_to_idx[int(target)]
        congestion = float(data.get("simulated_density", 1.0))
        adjacency[src_idx, dst_idx] += 1.0 / max(1.0, congestion)

    adjacency += np.eye(size, dtype=np.float32)
    degree = adjacency.sum(axis=1)
    inv_sqrt = np.diag(1.0 / np.sqrt(np.maximum(degree, 1e-6)))
    return inv_sqrt @ adjacency @ inv_sqrt


def _node_base_density(graph: nx.MultiDiGraph, node_ids: list[int]) -> np.ndarray:
    base = []
    for node_id in node_ids:
        incident = []
        for _, _, data in graph.out_edges(node_id, data=True):
            incident.append(float(data.get("simulated_density", 1.0)))
        for _, _, data in graph.in_edges(node_id, data=True):
            incident.append(float(data.get("simulated_density", 1.0)))
        base.append(float(np.mean(incident)) if incident else 0.5)
    return np.asarray(base, dtype=np.float32)


def _generate_history(graph: nx.MultiDiGraph, node_ids: list[int], steps: int) -> np.ndarray:
    rng = np.random.default_rng(RANDOM_SEED)
    base_density = _node_base_density(graph, node_ids)
    degrees = np.asarray([graph.degree(node_id) for node_id in node_ids], dtype=np.float32)
    degree_peak = float(np.max(degrees)) if len(degrees) else 1.0
    degree_signal = degrees / max(1.0, degree_peak)

    history = []
    for step in range(steps + 1):
        phase = (2.0 * math.pi * step) / max(steps, 1)
        wave = 0.55 * np.sin(phase + degree_signal * 1.7)
        rush = 0.35 * np.cos((phase * 0.5) + degree_signal * 2.3)
        noise = rng.normal(0.0, 0.08, size=len(node_ids))
        history.append(np.clip(base_density + wave + rush + noise + (degree_signal * 0.9), 0.05, 8.5))
    return np.asarray(history, dtype=np.float32)


def _analytic_forecast(graph: nx.MultiDiGraph) -> tuple[dict[int, float], PredictiveSummary]:
    node_ids, node_to_idx = _node_index(graph)
    adjacency = _normalized_adjacency(graph, node_to_idx)
    history = _generate_history(graph, node_ids, STGNN_HISTORY_STEPS)
    smoothed = (adjacency @ history[-1]) * 0.4 + history[-1] * 0.6
    forecast = np.clip((history[-1] * 0.65) + (history[-2] * 0.15) + (smoothed * 0.20), 0.05, 8.5)
    forecast_map = {node_id: float(forecast[idx]) for idx, node_id in enumerate(node_ids)}
    summary = PredictiveSummary(
        backend="analytic-fallback",
        node_count=len(node_ids),
        history_steps=STGNN_HISTORY_STEPS,
        training_loss=0.0,
        forecast_mean_density=float(np.mean(forecast)),
        forecast_peak_density=float(np.max(forecast)),
    )
    return forecast_map, summary


if torch is not None:

    class GraphConv(nn.Module):
        def __init__(self, input_dim: int, output_dim: int) -> None:
            super().__init__()
            self.linear = nn.Linear(input_dim, output_dim)

        def forward(self, features: torch.Tensor, adjacency: torch.Tensor) -> torch.Tensor:
            propagated = torch.einsum("ij,bjf->bif", adjacency, features)
            return self.linear(propagated)


    class STGNNModel(nn.Module):
        def __init__(self, hidden_dim: int) -> None:
            super().__init__()
            self.gconv1 = GraphConv(1, hidden_dim)
            self.gconv2 = GraphConv(hidden_dim, hidden_dim)
            self.temporal = nn.GRU(hidden_dim, hidden_dim, batch_first=True)
            self.head = nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim // 2),
                nn.ReLU(),
                nn.Linear(hidden_dim // 2, 1),
            )

        def forward(self, history: torch.Tensor, adjacency: torch.Tensor) -> torch.Tensor:
            # history: [batch, steps, nodes, features]
            batch_size, steps, nodes, features = history.shape
            spatial = history.reshape(batch_size * steps, nodes, features)
            spatial = torch.relu(self.gconv1(spatial, adjacency))
            spatial = torch.relu(self.gconv2(spatial, adjacency))
            spatial = spatial.reshape(batch_size, steps, nodes, -1)
            temporal_input = spatial.permute(0, 2, 1, 3).reshape(batch_size * nodes, steps, -1)
            temporal_output, _ = self.temporal(temporal_input)
            final_state = temporal_output[:, -1, :]
            prediction = self.head(final_state)
            return prediction.reshape(batch_size, nodes)


def _torch_forecast(graph: nx.MultiDiGraph) -> tuple[dict[int, float], PredictiveSummary]:
    assert torch is not None and nn is not None

    node_ids, node_to_idx = _node_index(graph)
    adjacency_np = _normalized_adjacency(graph, node_to_idx)
    history_np = _generate_history(graph, node_ids, STGNN_HISTORY_STEPS)

    adjacency = torch.tensor(adjacency_np, dtype=torch.float32)
    model = STGNNModel(hidden_dim=STGNN_HIDDEN_DIM)
    optimizer = torch.optim.Adam(model.parameters(), lr=STGNN_LEARNING_RATE)
    criterion = nn.MSELoss()

    input_history = torch.tensor(history_np[:-1], dtype=torch.float32).unsqueeze(0).unsqueeze(-1)
    target = torch.tensor(history_np[-1], dtype=torch.float32).unsqueeze(0)

    loss_value = 0.0
    model.train()
    for _ in range(STGNN_EPOCHS):
        optimizer.zero_grad()
        prediction = model(input_history, adjacency)
        loss = criterion(prediction, target)
        loss.backward()
        optimizer.step()
        loss_value = float(loss.item())

    model.eval()
    with torch.no_grad():
        forecast = model(input_history, adjacency).squeeze(0).cpu().numpy()

    forecast = np.clip(forecast, 0.05, 8.5)
    forecast_map = {node_id: float(forecast[idx]) for idx, node_id in enumerate(node_ids)}
    summary = PredictiveSummary(
        backend="pytorch-stgnn",
        node_count=len(node_ids),
        history_steps=STGNN_HISTORY_STEPS,
        training_loss=loss_value,
        forecast_mean_density=float(np.mean(forecast)),
        forecast_peak_density=float(np.max(forecast)),
    )
    return forecast_map, summary


def forecast_node_densities(graph: nx.MultiDiGraph) -> tuple[dict[int, float], PredictiveSummary]:
    if torch is None:
        return _analytic_forecast(graph)

    try:
        return _torch_forecast(graph)
    except Exception:
        return _analytic_forecast(graph)


def persist_predictive_state(
    forecast: dict[int, float],
    summary: PredictiveSummary,
    output_path: Path = PREDICTIVE_STATE_OUTPUT,
) -> None:
    payload = {
        "summary": asdict(summary),
        "forecast_by_node": {str(node_id): density for node_id, density in forecast.items()},
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
