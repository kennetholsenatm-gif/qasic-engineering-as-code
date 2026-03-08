"""
Superconducting extraction: kinetic inductance of traces and JJ nonlinear inductance from GDS/geometry.
Output: per-node and per-edge L (and optional decoherence contract) for routing/Hamiltonian.
Uses CPW (coplanar waveguide) geometry for L_k when width_um/gap_um are present; otherwise fallback.
Decoherence (gamma1, gamma2) derived from Quality Factor Q from C- and L-matrices, then T1/T2.
Ref: NEXT_STEPS_ROADMAP.md §1.1 Superconducting Extraction.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from typing import Any

import numpy as np

# Magnetic flux quantum (Wb). L_j = phi0 / (2*pi*Ic) for simple JJ model.
PHI0_WB = 2.067e-15

# Nominal frequency (Hz) for Q -> T1/T2 conversion (e.g. 5 GHz transmon).
DEFAULT_OMEGA_GHZ = 5.0


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


def extract_capacitance_matrix(manifest: dict[str, Any]) -> np.ndarray:
    """
    Return a mock Maxwell capacitance matrix C (in fF) for the cells.
    Shape (n_cells, n_cells). Diagonal = self-capacitance; off-diagonal = coupling.
    Assumptions: cells are nodes; C_ii from cell 'dimension' or constant; C_ij decays with distance
    (e.g. C_ij = C0_coup * exp(-d_ij/d0)). Units: fF (femtofarad).
    """
    cells = manifest.get("cells", [])
    pitch = manifest.get("pitch_um", 1.0)
    n = len(cells)
    if n == 0:
        return np.zeros((0, 0), dtype=float)
    positions = cell_positions(manifest, pitch)
    C_self_fF = 1.0
    C_coup_fF = 0.1
    d0_um = 2.0
    C = np.zeros((n, n), dtype=float)
    for i in range(n):
        dim_i = cells[i].get("dimension", 0.5)
        C[i, i] = C_self_fF * (0.5 + dim_i)
    for i in range(n):
        for j in range(i + 1, n):
            d = math.sqrt(
                (positions[i][0] - positions[j][0]) ** 2
                + (positions[i][1] - positions[j][1]) ** 2
            )
            coup = C_coup_fF * math.exp(-d / d0_um) if d > 1e-10 else 0.0
            C[i, j] = coup
            C[j, i] = coup
    return C


def cpw_kinetic_inductance_per_um(
    width_um: float,
    gap_um: float,
    L0_nH_per_um: float = 1e-5,
) -> float:
    """
    Kinetic inductance per unit length (nH/um) for a CPW (coplanar waveguide).
    Quasi-static approximation: L_k scales inversely with center conductor width and
    with gap (narrower width and smaller gap increase L_k). Formula:
    L_k_per_um = L0 / (width_um * (1 + 2*gap_um/width_um)) for typical CPW.
    L0_nH_per_um is a scaling constant (material/thickness dependent).
    """
    if width_um <= 0:
        width_um = 0.1
    if gap_um < 0:
        gap_um = 0.05
    factor = width_um * (1.0 + 2.0 * gap_um / width_um)
    return L0_nH_per_um / factor


def _decoherence_from_q(
    C_matrix_fF: np.ndarray,
    node_L_nH: list[float],
    omega_ghz: float = DEFAULT_OMEGA_GHZ,
    R_eff_ohm: float = 50.0,
    base_gamma1: float = 0.1,
    base_gamma2: float = 0.05,
) -> list[tuple[float, float]]:
    """
    Compute gamma1, gamma2 from Quality Factor Q derived from C- and L-matrices.
    Q = (1/R_eff) * sqrt(L_eff/C_eff) (LC oscillator); T1 = 2*Q/omega, gamma1 = 1/T1.
    T2 <= 2*T1 (dephasing); we use T2 = T1, gamma2 = 1/T2. Returns list of (gamma1, gamma2) per node.
    """
    n = len(node_L_nH)
    if n == 0 or C_matrix_fF.size == 0:
        return []
    omega_rad = 2.0 * math.pi * omega_ghz * 1e9
    # C in fF -> SI: 1e-15 F; L in nH -> SI: 1e-9 H
    C_si_scale = 1e-15
    L_si_scale = 1e-9
    out: list[tuple[float, float]] = []
    for k in range(n):
        L_eff = node_L_nH[k] * L_si_scale
        if L_eff <= 0:
            L_eff = 1e-12
        C_eff = C_matrix_fF[k, k] * C_si_scale
        if C_eff <= 0:
            C_eff = 1e-15
        Q = (1.0 / R_eff_ohm) * math.sqrt(L_eff / C_eff)
        if Q < 0.1:
            Q = 0.1
        T1_s = 2.0 * Q / omega_rad
        T1_us = T1_s * 1e6
        T2_us = T1_us  # placeholder: T2 <= 2*T1
        gamma1 = 1.0 / T1_s if T1_s > 1e-18 else base_gamma1
        gamma2 = 1.0 / (T2_us * 1e-6) if T2_us > 1e-6 else base_gamma2
        out.append((gamma1, gamma2))
    return out


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
    - Per-edge L: CPW formula when cells have width_um, gap_um; else length_um * L_per_um_nH.
    - Per-node L_kinetic: sum of half-lengths of incident traces.
    - JJ inductance: L_j = phi0 / (2*pi*Ic) if cells have "jj": true.
    - Decoherence: gamma1, gamma2 from Q (C- and L-matrices), then T1/T2; fallback to base_* when not computed.
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
        use_cpw_a = "width_um" in c and "gap_um" in c
        for di, dj in [(0, 1), (1, 0)]:
            nb = (i + di, j + dj)
            if nb in cell_index:
                k2 = cell_index[nb]
                c2 = cells[k2]
                use_cpw_b = "width_um" in c2 and "gap_um" in c2
                length_um = trace_length_um(c, c2, pitch_um)
                if use_cpw_a and use_cpw_b:
                    width_um = 0.5 * (c["width_um"] + c2["width_um"])
                    gap_um = 0.5 * (c["gap_um"] + c2["gap_um"])
                    L_per_um = cpw_kinetic_inductance_per_um(
                        width_um, gap_um, L0_nH_per_um=L_per_um_nH * 100.0
                    )
                    L_nH = length_um * L_per_um
                else:
                    L_nH = length_um * L_per_um_nH
                edges.append((k, k2, L_nH))

    # Per-node L: sum half of each incident edge
    node_L = [0.0] * n_cells
    for k, k2, L_nH in edges:
        node_L[k] += L_nH * 0.5
        node_L[k2] += L_nH * 0.5
    for k in range(n_cells):
        if node_L[k] == 0.0:
            if "width_um" in cells[k] and "gap_um" in cells[k]:
                node_L[k] = pitch_um * cpw_kinetic_inductance_per_um(
                    cells[k]["width_um"], cells[k]["gap_um"], L0_nH_per_um=L_per_um_nH * 100.0
                )
            else:
                node_L[k] = pitch_um * L_per_um_nH

    # JJ inductance L_j = phi0 / (2*pi*Ic); Ic in A
    Ic_A = Ic_ua * 1e-6
    L_j_nH = (PHI0_WB / (2 * math.pi * Ic_A)) * 1e9 if Ic_A > 0 else 0.0
    jj_list: list[dict[str, Any]] = []
    for k, c in enumerate(cells):
        if c.get("jj") is True:
            jj_list.append({"node": k, "L_j_nH": round(L_j_nH, 6)})

    # Decoherence from Q (C-matrix and L)
    C_matrix = extract_capacitance_matrix(manifest)
    gamma_list = _decoherence_from_q(
        C_matrix, node_L, base_gamma1=base_gamma1, base_gamma2=base_gamma2
    )
    nodes = []
    for k in range(n_cells):
        if k < len(gamma_list):
            g1, g2 = gamma_list[k]
        else:
            g1, g2 = base_gamma1, base_gamma2
        nodes.append({
            "gamma1": round(g1, 6),
            "gamma2": round(g2, 6),
            "L_kinetic_nH": round(node_L[k], 6),
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
