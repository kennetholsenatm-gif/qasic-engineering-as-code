"""
Graph Neural Network for metasurface inverse design: topology as graph (nodes + edges)
-> phase profile. Alternative to the MLP in metasurface_inverse_net.py for graph-structured inputs.
"""
from __future__ import annotations

import json
import math
from typing import Optional

import numpy as np
import torch
import torch.nn as nn


def routing_json_to_graph(
    routing_path: str,
    node_feature_dim: int = 8,
) -> tuple[torch.Tensor, torch.Tensor]:
    """
    Read routing JSON; return node features (N, node_feature_dim) and edge_index (2, E).
    Nodes = logical qubits / physical nodes from mapping; edges = interaction pairs (linear chain).
    """
    with open(routing_path, encoding="utf-8") as f:
        data = json.load(f)
    mapping = data.get("mapping", [])
    if not mapping:
        mapping = [{"logical": 0, "physical": 0}, {"logical": 1, "physical": 1}, {"logical": 2, "physical": 2}]
    n = len(mapping)
    # Node features: [logical, physical, one-hot style or normalized]
    features = []
    for m in mapping:
        log_ = float(m.get("logical", 0))
        phys_ = float(m.get("physical", 0))
        row = [log_ / max(n, 1), phys_ / max(n, 1)]
        while len(row) < node_feature_dim:
            row.append(0.0)
        features.append(row[:node_feature_dim])
    x = torch.tensor(features, dtype=torch.float32)
    # Edges: linear chain (i, i+1)
    edge_list = []
    for i in range(n - 1):
        edge_list.append([i, i + 1])
        edge_list.append([i + 1, i])
    if not edge_list:
        edge_list = [[0, 0]]
    edge_index = torch.tensor(edge_list, dtype=torch.long).t().contiguous()  # (2, E)
    return x, edge_index


class MetasurfaceInverseGNN(nn.Module):
    """
    GNN: node features + edge_index -> message passing -> global readout -> MLP -> phase profile.
    Same output contract as MetasurfaceInverseNet: (batch, num_meta_atoms) in [0, 2*pi] or phase band.
    """

    def __init__(
        self,
        node_feature_dim: int,
        num_meta_atoms: int,
        hidden: int = 128,
        num_layers: int = 3,
        phase_lo: float | None = None,
        phase_hi: float | None = None,
    ):
        super().__init__()
        self.node_feature_dim = node_feature_dim
        self.num_meta_atoms = num_meta_atoms
        self.phase_lo = phase_lo
        self.phase_hi = phase_hi
        self.hidden = hidden
        self.num_layers = num_layers
        self.node_embed = nn.Linear(node_feature_dim, hidden)
        self.message_layers = nn.ModuleList([
            nn.Linear(2 * hidden, hidden) for _ in range(num_layers)
        ])
        self.readout = nn.Sequential(
            nn.Linear(hidden, hidden * 2),
            nn.ReLU(inplace=True),
            nn.Linear(hidden * 2, num_meta_atoms),
        )
        self.sigmoid = nn.Sigmoid()

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        batch: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        x: (N, node_feature_dim), edge_index: (2, E).
        batch: (N,) optional batch index for multiple graphs; if None, single graph.
        return: (batch_size, num_meta_atoms) phases.
        """
        n = x.size(0)
        h = self.node_embed(x)  # (N, hidden)
        for layer in self.message_layers:
            # Message: for each edge (i,j), concat h_i, h_j -> message
            src, tgt = edge_index[0], edge_index[1]
            msg = torch.cat([h[src], h[tgt]], dim=1)  # (E, 2*hidden)
            out = layer(msg)  # (E, hidden)
            # Aggregate: scatter add to nodes
            agg = torch.zeros(n, out.size(1), device=out.device, dtype=out.dtype)
            agg.index_add_(0, tgt, out)
            h = h + agg
            h = torch.relu(h)
        # Global readout: mean over nodes
        if batch is not None:
            batch_size = int(batch.max().item()) + 1
            g = torch.zeros(batch_size, h.size(1), device=h.device, dtype=h.dtype)
            g.scatter_add_(0, batch.unsqueeze(1).expand_as(h), h)
            counts = torch.zeros(batch_size, 1, device=h.device, dtype=h.dtype)
            counts.scatter_add_(0, batch.unsqueeze(1), torch.ones_like(batch.unsqueeze(1), dtype=h.dtype))
            g = g / counts.clamp(min=1)
        else:
            g = h.mean(dim=0, keepdim=True)  # (1, hidden)
        raw = self.readout(g)
        if self.phase_lo is not None and self.phase_hi is not None:
            return self.sigmoid(raw) * (self.phase_hi - self.phase_lo) + self.phase_lo
        return self.sigmoid(raw) * (2 * math.pi)


def drc_penalty_tensor(
    phases: torch.Tensor,
    min_width_um: float = 0.1,
    min_spacing_um: float = 0.05,
) -> torch.Tensor:
    """
    Differentiable DRC proxy: penalize large phase gradients (proxy for min feature / spacing).
    Use as an extra loss term: loss = mse_loss + scale * drc_penalty_tensor(phases).
    Ref: NEXT_STEPS_ROADMAP.md §6.2 Physics-Informed GNN (DRC in loss).
    """
    if phases.dim() == 1:
        phases = phases.unsqueeze(0)
    # Reshape to 2D grid if possible (sqrt)
    n = phases.size(-1)
    s = int(n ** 0.5)
    if s * s == n:
        p = phases.view(-1, s, s)
        dx = (p[:, 1:, :] - p[:, :-1, :]).abs().mean()
        dy = (p[:, :, 1:] - p[:, :, :-1]).abs().mean()
        penalty = dx + dy  # larger gradient -> larger penalty
    else:
        penalty = torch.tensor(0.0, device=phases.device, dtype=phases.dtype)
    return penalty


def create_gnn_model(
    node_feature_dim: int = 8,
    num_meta_atoms: int = 1000,
    device: str | torch.device = "cpu",
    phase_band: tuple[float, float] | None = None,
    hidden: int = 128,
    num_layers: int = 3,
) -> MetasurfaceInverseGNN:
    model = MetasurfaceInverseGNN(
        node_feature_dim=node_feature_dim,
        num_meta_atoms=num_meta_atoms,
        hidden=hidden,
        num_layers=num_layers,
        phase_lo=phase_band[0] if phase_band else None,
        phase_hi=phase_band[1] if phase_band else None,
    )
    return model.to(device)
