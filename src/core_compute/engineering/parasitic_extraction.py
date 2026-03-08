"""
Parasitic extraction: from geometry manifest (and optional routing), compute per-node
decoherence contributions from layout proximity (distances, simple coupling proxy).
Output: JSON in same format as decoherence_rates expects (nodes with gamma1, gamma2).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from typing import Any

import numpy as np


def load_manifest(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_routing(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def cell_positions(manifest: dict[str, Any], pitch_um: float = 1.0) -> list[tuple[float, float]]:
    """Return list of (x, y) in um for each cell (i, j) * pitch."""
    pitch = manifest.get("pitch_um", pitch_um)
    return [(c["j"] * pitch, c["i"] * pitch) for c in manifest.get("cells", [])]


def pairwise_distances(positions: list[tuple[float, float]]) -> np.ndarray:
    """N x N matrix of Euclidean distances (um)."""
    n = len(positions)
    d = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            dx = positions[i][0] - positions[j][0]
            dy = positions[i][1] - positions[j][1]
            dist = math.sqrt(dx * dx + dy * dy)
            d[i, j] = d[j, i] = dist
    return d


def coupling_proxy(distance_um: float, scale: float = 0.1, min_dist_um: float = 0.5) -> float:
    """Simple proxy: coupling ~ scale / max(distance, min_dist)."""
    return scale / max(distance_um, min_dist_um)


def extract_decoherence_from_manifest(
    manifest_path: str,
    routing_path: str | None,
    base_gamma1: float = 0.1,
    base_gamma2: float = 0.05,
    coupling_scale: float = 0.01,
) -> dict[str, Any]:
    """
    Build decoherence file from layout: per-node rates = base + sum of coupling from neighbors.
    If routing_path given, num_nodes = num_physical_nodes and we assign one "node" per logical
    (physical) position; else num_nodes = num_cells and each cell is a node.
    """
    manifest = load_manifest(manifest_path)
    positions = cell_positions(manifest)
    n_cells = len(positions)
    if n_cells == 0:
        return {"nodes": [{"gamma1": base_gamma1, "gamma2": base_gamma2}], "source": "parasitic_extraction"}

    dist = pairwise_distances(positions)
    # Per-cell extra rate from neighbors (inverse distance proxy)
    extra = np.zeros(n_cells)
    for i in range(n_cells):
        for j in range(n_cells):
            if i != j and dist[i, j] > 0:
                extra[i] += coupling_proxy(dist[i, j], scale=coupling_scale)

    if routing_path and os.path.isfile(routing_path):
        routing = load_routing(routing_path)
        n_nodes = int(routing.get("num_physical_nodes", n_cells))
        # Map physical node index to cell indices (simplified: node k = cell k if n_nodes == n_cells)
        if n_nodes <= n_cells:
            nodes = []
            for k in range(n_nodes):
                gamma1 = base_gamma1 + float(extra[k]) if k < n_cells else base_gamma1
                gamma2 = base_gamma2 + float(extra[k]) * 0.5 if k < n_cells else base_gamma2
                nodes.append({"gamma1": round(gamma1, 6), "gamma2": round(gamma2, 6)})
        else:
            nodes = [{"gamma1": base_gamma1, "gamma2": base_gamma2} for _ in range(n_nodes)]
        return {"nodes": nodes, "num_physical_nodes": n_nodes, "source": "parasitic_extraction", "manifest_ref": manifest_path}
    else:
        nodes = []
        for i in range(n_cells):
            gamma1 = base_gamma1 + float(extra[i])
            gamma2 = base_gamma2 + float(extra[i]) * 0.5
            nodes.append({"gamma1": round(gamma1, 6), "gamma2": round(gamma2, 6)})
        return {"nodes": nodes, "source": "parasitic_extraction", "manifest_ref": manifest_path}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract layout-aware decoherence rates from geometry manifest.",
    )
    parser.add_argument("manifest", help="Path to geometry_manifest.json")
    parser.add_argument("--routing", default=None, help="Path to routing.json (optional)")
    parser.add_argument("-o", "--output", default=None, help="Output JSON path (decoherence file)")
    parser.add_argument("--gamma1", type=float, default=0.1, help="Base gamma1 per node")
    parser.add_argument("--gamma2", type=float, default=0.05, help="Base gamma2 per node")
    args = parser.parse_args()

    if not os.path.isfile(args.manifest):
        print(f"Manifest not found: {args.manifest}", file=sys.stderr)
        return 1

    data = extract_decoherence_from_manifest(
        args.manifest,
        args.routing,
        base_gamma1=args.gamma1,
        base_gamma2=args.gamma2,
    )
    out_path = args.output
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"Wrote {out_path} ({len(data['nodes'])} nodes)")
    else:
        print(json.dumps(data, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
