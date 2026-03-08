"""
Cryogenic thermal stage model: power from routing + phase profile -> temperatures at 10 mK, 4 K, 50 K.
Simplified lumped thermal network (no full FEA) so CI and lightweight runs succeed.
Output: *_thermal_report.json for integration with thermodynamic_validator.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import numpy as np

# Thermal budget (whitepaper): 18 nW/cell proxy; 10 mK stage must stay cold
NW_PER_CELL_LIMIT = 18.0
T_10MK_LIMIT_K = 0.015  # ~15 mK max
T_4K_LIMIT_K = 5.0
T_50K_LIMIT_K = 55.0


def load_routing(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_phases(path: str) -> np.ndarray:
    arr = np.load(path)
    return np.asarray(arr, dtype=np.float64).ravel()


def power_proxy_from_phases(phases_rad: np.ndarray, nw_per_cell: float = NW_PER_CELL_LIMIT) -> np.ndarray:
    """Phase deviation from pi as proxy for power (higher deviation -> more dissipation)."""
    dev = np.abs(phases_rad - np.pi)
    return np.minimum(dev * (nw_per_cell / 0.14), nw_per_cell * 2.0)  # cap


def thermal_report(
    routing_json_path: str,
    phases_path: str,
    nw_per_cell_limit: float = NW_PER_CELL_LIMIT,
) -> dict[str, Any]:
    """
    Compute lumped thermal report: total power, per-stage proxy temperatures.
    Model: P_total = sum over cells of power_proxy(phase); T_stage = T_base + R_th * P_total (simple).
    """
    routing = load_routing(routing_json_path)
    phases = load_phases(phases_path)
    n_cells = phases.size
    power_per_cell = power_proxy_from_phases(phases, nw_per_cell_limit)
    P_total_nw = float(np.sum(power_per_cell))
    P_mean_nw = float(np.mean(power_per_cell)) if n_cells else 0.0

    # Lumped resistance proxy (K/nW): arbitrary scale for reporting
    R_10mK = 1e-6
    R_4K = 1e-7
    R_50K = 1e-8
    T_10mK = 0.01 + R_10mK * P_total_nw
    T_4K = 4.0 + R_4K * P_total_nw
    T_50K = 50.0 + R_50K * P_total_nw

    passed_10mK = T_10mK <= T_10MK_LIMIT_K
    passed_4K = T_4K <= T_4K_LIMIT_K
    passed_50K = T_50K <= T_50K_LIMIT_K
    passed = passed_10mK and passed_4K and passed_50K

    return {
        "num_cells": n_cells,
        "P_total_nW": round(P_total_nw, 4),
        "P_mean_nW_per_cell": round(P_mean_nw, 4),
        "nw_per_cell_limit": nw_per_cell_limit,
        "T_10mK_K": round(T_10mK, 6),
        "T_4K_K": round(T_4K, 4),
        "T_50K_K": round(T_50K, 4),
        "T_10mK_limit_K": T_10MK_LIMIT_K,
        "passed_10mK": passed_10mK,
        "passed_4K": passed_4K,
        "passed_50K": passed_50K,
        "passed": passed,
        "routing_ref": routing_json_path,
        "phases_ref": phases_path,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Thermal stage report from routing + phase array (lumped model).",
    )
    parser.add_argument("routing_json", help="Path to routing JSON")
    parser.add_argument("phases_npy", help="Path to phases .npy")
    parser.add_argument("-o", "--output", default=None, help="Output JSON report path")
    parser.add_argument("--nw-limit", type=float, default=NW_PER_CELL_LIMIT, help="nW per cell limit")
    args = parser.parse_args()

    if not os.path.isfile(args.routing_json):
        print(f"Routing file not found: {args.routing_json}", file=sys.stderr)
        return 1
    if not os.path.isfile(args.phases_npy):
        print(f"Phases file not found: {args.phases_npy}", file=sys.stderr)
        return 1

    report = thermal_report(args.routing_json, args.phases_npy, args.nw_limit)
    out_path = args.output
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"Wrote {out_path}")
    else:
        print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
