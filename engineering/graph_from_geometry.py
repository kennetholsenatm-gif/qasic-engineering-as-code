"""
Build physics-aligned graphs for the metasurface GNN (Graph-Theoretic Inverse Design whitepaper).
Nodes = meta-atoms; node features from 2D coordinates (and optional ω); edges from grid
connectivity or from a coupling matrix (coupled-mode / SuperScreen).
"""
from __future__ import annotations

import os
import sys
from typing import Any

import numpy as np
import torch


def grid_2d_graph(
    nx: int,
    ny: int,
    node_feature_dim: int = 8,
    normalize: bool = True,
) -> tuple[torch.Tensor, torch.Tensor]:
    """
    Build graph from a regular 2D grid of meta-atoms (e.g. nx*ny array).
    Node features: [px_norm, py_norm, 0, ...]; edges = 4-neighbor connectivity.
    Returns x (N, node_feature_dim), edge_index (2, E).
    """
    n = nx * ny
    # Node features: normalized (px, py)
    rows = np.arange(ny, dtype=np.float64).reshape(-1, 1).repeat(nx, axis=1).ravel()
    cols = np.arange(nx, dtype=np.float64).reshape(1, -1).repeat(ny, axis=0).ravel()
    if normalize:
        rows = rows / max(ny - 1, 1)
        cols = cols / max(nx - 1, 1)
    features = np.zeros((n, node_feature_dim), dtype=np.float32)
    features[:, 0] = rows
    features[:, 1] = cols
    x = torch.from_numpy(features)

    # 4-neighbor edges: (i, j) and (j, i) for undirected
    edge_list = []
    for i in range(ny):
        for j in range(nx):
            u = i * nx + j
            if j + 1 < nx:
                v = i * nx + (j + 1)
                edge_list.append([u, v])
                edge_list.append([v, u])
            if i + 1 < ny:
                v = (i + 1) * nx + j
                edge_list.append([u, v])
                edge_list.append([v, u])
    if not edge_list:
        edge_list = [[0, 0]]
    edge_index = torch.tensor(edge_list, dtype=torch.long).t().contiguous()
    return x, edge_index


def coupling_matrix_to_graph(
    coupling: np.ndarray,
    positions_xy: np.ndarray | None = None,
    node_feature_dim: int = 8,
    threshold: float = 0.0,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor | None]:
    """
    Build graph from coupling matrix (e.g. from coupled-mode Ω or mutual inductance).
    coupling[i,j] = coupling strength; edges for |coupling[i,j]| > threshold (i != j).
    Node features: from positions_xy (px, py normalized) if given, else index-based.
    Returns x (N, node_feature_dim), edge_index (2, E), edge_attr (E,) or None.
    """
    coupling = np.asarray(coupling, dtype=np.float64)
    n = coupling.shape[0]
    if coupling.shape[1] != n:
        raise ValueError("Coupling matrix must be square")

    if positions_xy is not None:
        pos = np.asarray(positions_xy, dtype=np.float64)
        if pos.shape[0] != n or pos.shape[1] < 2:
            raise ValueError("positions_xy must be (n, 2) or (n, >=2)")
        px = pos[:, 0]
        py = pos[:, 1]
        px = (px - px.min()) / max(px.max() - px.min(), 1e-9)
        py = (py - py.min()) / max(py.max() - py.min(), 1e-9)
        features = np.zeros((n, node_feature_dim), dtype=np.float32)
        features[:, 0] = px
        features[:, 1] = py
    else:
        features = np.zeros((n, node_feature_dim), dtype=np.float32)
        idx_norm = np.arange(n, dtype=np.float32) / max(n - 1, 1)
        features[:, 0] = idx_norm

    x = torch.from_numpy(features)

    edge_list = []
    edge_vals = []
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            c = coupling[i, j]
            if abs(c) > threshold:
                edge_list.append([i, j])
                edge_vals.append(float(c))
    if not edge_list:
        edge_list = [[0, 0]]
        edge_vals = [0.0]
    edge_index = torch.tensor(edge_list, dtype=torch.long).t().contiguous()
    edge_attr = torch.tensor(edge_vals, dtype=torch.float32)
    return x, edge_index, edge_attr


def routing_json_to_geometry_graph(
    routing_path: str,
    node_feature_dim: int = 8,
) -> tuple[torch.Tensor, torch.Tensor]:
    """
    Build graph from routing JSON: same contract as metasurface_inverse_gnn.routing_json_to_graph
    (linear chain from mapping). Provided so geometry-based builders can be swapped in later
    (e.g. replace with grid_2d_graph or coupling_matrix_to_graph when coupling is available).
    """
    try:
        from engineering.metasurface_inverse_gnn import routing_json_to_graph
    except ImportError:
        from metasurface_inverse_gnn import routing_json_to_graph
    return routing_json_to_graph(routing_path, node_feature_dim)


def save_graph_for_gnn(
    x: torch.Tensor,
    edge_index: torch.Tensor,
    path_base: str,
    edge_attr: torch.Tensor | None = None,
) -> None:
    """
    Save graph tensors for later use (e.g. by a training script).
    Writes path_base_x.pt, path_base_edge_index.pt, and optionally path_base_edge_attr.pt.
    """
    torch.save(x, path_base + "_x.pt")
    torch.save(edge_index, path_base + "_edge_index.pt")
    if edge_attr is not None:
        torch.save(edge_attr, path_base + "_edge_attr.pt")


def load_graph_for_gnn(path_base: str) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor | None]:
    """Load x, edge_index, edge_attr from path_base_*.pt (weights_only=True for safe deserialization)."""
    x = torch.load(path_base + "_x.pt", weights_only=True)
    edge_index = torch.load(path_base + "_edge_index.pt", weights_only=True)
    edge_attr_path = path_base + "_edge_attr.pt"
    edge_attr = torch.load(edge_attr_path, weights_only=True) if os.path.isfile(edge_attr_path) else None
    return x, edge_index, edge_attr


def main() -> int:
    """CLI: build graph from grid or from JSON (routing or coupling)."""
    import argparse
    parser = argparse.ArgumentParser(
        description="Build physics-aligned graph for metasurface GNN (grid or coupling matrix).",
    )
    parser.add_argument(
        "--grid",
        type=str,
        default=None,
        metavar="NX,NY",
        help="Build 2D grid graph with NX x NY nodes (e.g. 10,10).",
    )
    parser.add_argument(
        "--routing",
        type=str,
        default=None,
        metavar="FILE",
        help="Use routing JSON to build linear-chain graph (same as GNN pipeline).",
    )
    parser.add_argument(
        "--node-dim",
        type=int,
        default=8,
        help="Node feature dimension (default 8).",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        metavar="BASE",
        help="Save graph tensors to BASE_x.pt, BASE_edge_index.pt [, BASE_edge_attr.pt].",
    )
    args = parser.parse_args()

    if args.grid:
        parts = [p.strip() for p in args.grid.split(",")]
        if len(parts) != 2:
            print("--grid must be NX,NY", file=sys.stderr)
            return 1
        nx, ny = int(parts[0]), int(parts[1])
        x, edge_index = grid_2d_graph(nx, ny, node_feature_dim=args.node_dim)
        edge_attr = None
    elif args.routing and os.path.isfile(args.routing):
        x, edge_index = routing_json_to_geometry_graph(args.routing, args.node_dim)
        edge_attr = None
    else:
        print("Use --grid NX,NY or --routing FILE", file=sys.stderr)
        return 1

    print(f"Nodes: {x.size(0)}  Edges: {edge_index.size(1)}  Node dim: {x.size(1)}")
    if args.output:
        save_graph_for_gnn(x, edge_index, args.output, edge_attr)
        print(f"Saved to {args.output}_x.pt, {args.output}_edge_index.pt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
