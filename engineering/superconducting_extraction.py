"""
Superconducting extraction: kinetic inductance of traces and JJ nonlinear inductance from GDS/geometry.
Output: per-node and per-edge L (and optional decoherence contract) for routing/Hamiltonian.
Ref: NEXT_STEPS_ROADMAP.md §1.1 Superconducting Extraction.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from typing import Any

# Magnetic flux quantum (Wb). L_j = phi0 / (2*pi*Ic) for simple JJ model.
PHI0_WB = 2.067e-15


def load_manifest(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_routing(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def cell_positions(manifest: dict[str, Any], pitch_um: float = 1.0) -> list[tuple[float, float]]:
    """Return list of (x, y) in um for each cell."""
    pitch = manifest.get("pitch_um", pitch_um)
    return [(c["j"] * pitch, c["i"] * pitch) for c in manifest.get("cells", [])]


def trace_length_um(cell_a: dict[str, Any], cell_b: dict[str, Any], pitch_um: float) -> float:
    """Estimate trace length between two cells (Manhattan or Euclidean)."""
    dx = (cell_b["j"] - cell_a["j"]) * pitch_um
    dy = (cell_b["i"] - cell_a["i"]) * pitch_um
    return math.sqrt(dx * dx + dy * dy)


def extract_kinetic_inductance(
    manifest_path: str,
    routing_path: str | None = None,
    L_per_um_nH: float = 1e-6,
    Ic_ua: float = 1.0,
    base_gamma1: float = 0.1,
    base_gamma2: float = 0.05,
) -> dict[str, Any]:
    """
    Extract kinetic inductance from geometry manifest.
    - Per-node L_kinetic: sum of half-lengths of incident traces (length_um * L_per_um_nH).
    - Per-edge L_kinetic: trace length between adjacent cells (linear chain or from routing).
    - JJ inductance: L_j = phi0 / (2*pi*Ic) if cells have "jj": true or explicit jj list.
    Output includes nodes with gamma1, gamma2 (from L proxy) and L_kinetic_nH for Hamiltonian use.
    """
    manifest = load_manifest(manifest_path)
    cells = manifest.get("cells", [])
    pitch_um = manifest.get("pitch_um", 1.0)
    n_cells = len(cells)
    if n_cells == 0:
        return {
            "nodes": [{"gamma1": base_gamma1, "gamma2": base_gamma2, "L_kinetic_nH": 0.0}],
            "edges": [],
            "jj": [],
            "source": "superconducting_extraction",
            "manifest_ref": manifest_path,
        }

    # Build adjacency: linear chain (i, j) <-> (i, j+1) and (i, j) <-> (i+1, j)
    def cell_key(c: dict[str, Any]) -> tuple[int, int]:
        return (c["i"], c["j"])

    cell_index = {cell_key(c): k for k, c in enumerate(cells)}
    edges: list[tuple[int, int, float]] = []
    for k, c in enumerate(cells):
        i, j = c["i"], c["j"]
        for di, dj in [(0, 1), (1, 0)]:
            nb = (i + di, j + dj)
            if nb in cell_index:
                k2 = cell_index[nb]
                length_um = trace_length_um(c, cells[k2], pitch_um)
                L_nH = length_um * L_per_um_nH
                edges.append((k, k2, L_nH))

    # Per-node L: sum half of each incident edge (or self-loop from cell "dimension" as proxy length)
    node_L = [0.0] * n_cells
    for k, k2, L_nH in edges:
        node_L[k] += L_nH * 0.5
        node_L[k2] += L_nH * 0.5
    # Isolated nodes: use pitch as proxy trace length
    for k in range(n_cells):
        if node_L[k] == 0.0:
            node_L[k] = pitch_um * L_per_um_nH

    # JJ inductance L_j = phi0 / (2*pi*Ic); Ic in A
    Ic_A = Ic_ua * 1e-6
    L_j_nH = (PHI0_WB / (2 * math.pi * Ic_A)) * 1e9 if Ic_A > 0 else 0.0
    jj_list: list[dict[str, Any]] = []
    for k, c in enumerate(cells):
        if c.get("jj") is True:
            jj_list.append({"node": k, "L_j_nH": round(L_j_nH, 6)})

    # Decoherence proxy: higher L -> higher flux noise sensitivity -> increase gamma_phi
    # Simple: gamma2 += scale * L_kinetic_nH
    scale_l_to_gamma = 0.001
    nodes = []
    for k in range(n_cells):
        Lk = node_L[k]
        extra = Lk * scale_l_to_gamma
        gamma1 = round(base_gamma1 + extra * 0.5, 6)
        gamma2 = round(base_gamma2 + extra, 6)
        nodes.append({
            "gamma1": gamma1,
            "gamma2": gamma2,
            "L_kinetic_nH": round(Lk, 6),
        })

    n_nodes = n_cells
    if routing_path and os.path.isfile(routing_path):
        routing = load_routing(routing_path)
        n_nodes = int(routing.get("num_physical_nodes", n_cells))
        if n_nodes > n_cells:
            for _ in range(n_nodes - n_cells):
                nodes.append({
                    "gamma1": base_gamma1,
                    "gamma2": base_gamma2,
                    "L_kinetic_nH": 0.0,
                })

    edge_list = [
        {"i": k, "j": k2, "L_kinetic_nH": round(L_nH, 6)}
        for k, k2, L_nH in edges
    ]

    return {
        "nodes": nodes,
        "num_physical_nodes": n_nodes if routing_path and os.path.isfile(routing_path) else None,
        "edges": edge_list,
        "jj": jj_list,
        "source": "superconducting_extraction",
        "manifest_ref": manifest_path,
        "L_per_um_nH": L_per_um_nH,
        "Ic_ua": Ic_ua,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract kinetic inductance (and JJ L) from geometry manifest for superconducting tapeout.",
    )
    parser.add_argument("manifest", help="Path to geometry_manifest.json")
    parser.add_argument("--routing", default=None, help="Path to routing.json (optional)")
    parser.add_argument("-o", "--output", default=None, help="Output JSON path (default: *_kinetic_inductance.json)")
    parser.add_argument("--L-per-um", type=float, default=1e-6, dest="L_per_um_nH", help="Kinetic inductance per um (nH)")
    parser.add_argument("--Ic-ua", type=float, default=1.0, help="Critical current for JJ L (uA)")
    parser.add_argument("--gamma1", type=float, default=0.1, help="Base gamma1 for decoherence output")
    parser.add_argument("--gamma2", type=float, default=0.05, help="Base gamma2 for decoherence output")
    args = parser.parse_args()

    if not os.path.isfile(args.manifest):
        print(f"Manifest not found: {args.manifest}", file=sys.stderr)
        return 1

    data = extract_kinetic_inductance(
        args.manifest,
        args.routing,
        L_per_um_nH=args.L_per_um_nH,
        Ic_ua=args.Ic_ua,
        base_gamma1=args.gamma1,
        base_gamma2=args.gamma2,
    )
    out_path = args.output
    if not out_path:
        base = os.path.splitext(args.manifest)[0]
        out_path = base + "_kinetic_inductance.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Wrote {out_path} ({len(data['nodes'])} nodes, {len(data['edges'])} edges, {len(data['jj'])} JJs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
