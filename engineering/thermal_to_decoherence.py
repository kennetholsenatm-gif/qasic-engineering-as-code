"""
Map thermal stage output (per-node temperature or thermal risk) to decoherence rates (gamma1, gamma2).
Consumers: decoherence_rates, open_system_qutip, routing with decoherence penalty.
Ref: NEXT_STEPS_ROADMAP.md §3.1 Closed-Loop Noise (Thermal → Decoherence).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np


def load_thermal_report(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_routing(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_phases(path: str) -> np.ndarray:
    arr = np.load(path)
    return np.asarray(arr, dtype=np.float64).ravel()


def power_proxy_from_phases(phases_rad: np.ndarray, nw_per_cell: float = 18.0) -> np.ndarray:
    """Phase deviation from pi as power proxy (same as thermal_stages)."""
    dev = np.abs(phases_rad - np.pi)
    return np.minimum(dev * (nw_per_cell / 0.14), nw_per_cell * 2.0)


def thermal_risk_to_gamma(
    T_bath_K: float,
    base_gamma1: float = 0.1,
    base_gamma2: float = 0.05,
    T_ref_K: float = 0.015,
) -> tuple[float, float]:
    """
    Map bath temperature to gamma1, gamma2. Simple model: gamma1 ∝ T (or 1/T1 with T1 ∝ 1/T).
    Higher T -> higher gamma.
    """
    if T_bath_K <= 0:
        return base_gamma1, base_gamma2
    # Scale: at T_ref, use base; above T_ref, increase
    scale = T_bath_K / max(T_ref_K, 1e-6)
    gamma1 = base_gamma1 * min(scale, 10.0)
    gamma2 = base_gamma2 * min(scale, 10.0)
    return round(gamma1, 6), round(gamma2, 6)


def build_decoherence_from_thermal(
    thermal_report_path: str,
    routing_path: str | None = None,
    phases_path: str | None = None,
    n_nodes: int | None = None,
    base_gamma1: float = 0.1,
    base_gamma2: float = 0.05,
) -> dict[str, Any]:
    """
    Build decoherence JSON from thermal report. If phases_path and routing_path given,
    compute per-node thermal risk from power_per_cell and mapping; else use lumped T_10mK for all nodes.
    """
    report = load_thermal_report(thermal_report_path)
    T_10mK = report.get("T_10mK_K", 0.015)
    num_cells = report.get("num_cells", 3)
    if n_nodes is None:
        n_nodes = num_cells
    if routing_path and os.path.isfile(routing_path) and phases_path and os.path.isfile(phases_path):
        routing = load_routing(routing_path)
        phases = load_phases(phases_path)
        power_per_cell = power_proxy_from_phases(phases)
        n_phys = int(routing.get("num_physical_nodes", len(power_per_cell)))
        n_nodes = max(n_nodes, n_phys)
        # Per-node temperature proxy: map cells to nodes (simplified: node k = cell k)
        node_T = np.zeros(n_nodes)
        for k in range(min(n_nodes, len(power_per_cell))):
            node_T[k] = T_10mK + 1e-6 * power_per_cell[k] if k < len(power_per_cell) else T_10mK
        for k in range(len(power_per_cell), n_nodes):
            node_T[k] = T_10mK
        nodes = []
        for k in range(n_nodes):
            g1, g2 = thermal_risk_to_gamma(float(node_T[k]), base_gamma1, base_gamma2)
            nodes.append({"gamma1": g1, "gamma2": g2})
    else:
        g1, g2 = thermal_risk_to_gamma(T_10mK, base_gamma1, base_gamma2)
        nodes = [{"gamma1": g1, "gamma2": g2} for _ in range(n_nodes)]
    return {
        "nodes": nodes,
        "source": "thermal_to_decoherence",
        "thermal_report_ref": thermal_report_path,
        "num_nodes": n_nodes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Map thermal report to decoherence file (per-node gamma1, gamma2).",
    )
    parser.add_argument("thermal_report", help="Path to thermal_report.json")
    parser.add_argument("-o", "--output", default=None, help="Output decoherence JSON path")
    parser.add_argument("--routing", default=None, help="Path to routing.json (optional, for per-node risk)")
    parser.add_argument("--phases", default=None, help="Path to phases .npy (optional, with --routing)")
    parser.add_argument("--n-nodes", type=int, default=None, help="Number of nodes (default from report)")
    parser.add_argument("--gamma1", type=float, default=0.1, help="Base gamma1")
    parser.add_argument("--gamma2", type=float, default=0.05, help="Base gamma2")
    args = parser.parse_args()

    if not os.path.isfile(args.thermal_report):
        print(f"Thermal report not found: {args.thermal_report}", file=sys.stderr)
        return 1

    data = build_decoherence_from_thermal(
        args.thermal_report,
        routing_path=args.routing,
        phases_path=args.phases,
        n_nodes=args.n_nodes,
        base_gamma1=args.gamma1,
        base_gamma2=args.gamma2,
    )
    out_path = args.output
    if not out_path:
        base = Path(args.thermal_report).stem.replace("_thermal_report", "")
        out_path = str(Path(args.thermal_report).parent / (base + "_decoherence_from_thermal.json"))
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Wrote {out_path} ({len(data['nodes'])} nodes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
