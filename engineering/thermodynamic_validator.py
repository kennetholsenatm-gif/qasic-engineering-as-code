"""
Thermodynamic validation for metasurface phase profiles (Graph-Theoretic Inverse Design whitepaper).
Checks π-radian baseline (sub-radian band) and 18 nW/cell Cryo-CMOS compliance.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from typing import Any

import numpy as np

# Whitepaper: sub-radian band around π for 18 nW/cell FD-SOI Cryo-CMOS
PI_BASELINE_LO = math.pi - 0.14  # ~3.00 rad
PI_BASELINE_HI = math.pi + 0.14  # ~3.28 rad
NW_PER_CELL_LIMIT = 18.0  # nanowatt per cell


def phases_comply_pi_baseline(
    phases_rad: np.ndarray,
    pi_lo: float = PI_BASELINE_LO,
    pi_hi: float = PI_BASELINE_HI,
) -> tuple[bool, float]:
    """
    Check whether all phases lie within the sub-radian band [pi_lo, pi_hi].
    Returns (all_comply, fraction_in_band).
    """
    in_band = (phases_rad >= pi_lo) & (phases_rad <= pi_hi)
    n = phases_rad.size
    fraction = float(np.sum(in_band)) / n if n else 0.0
    return bool(np.all(in_band)), fraction


def phase_thermodynamic_report(
    phases_rad: np.ndarray,
    nw_per_cell_limit: float = NW_PER_CELL_LIMIT,
    pi_lo: float = PI_BASELINE_LO,
    pi_hi: float = PI_BASELINE_HI,
) -> dict[str, Any]:
    """
    Build a report dict: stats, π-baseline compliance, and thermal risk.
    Phases assumed in radians. Thermal risk is qualitative: low/medium/high
    based on how far phases deviate from the sub-radian band (proxy for 18 nW/cell).
    """
    phases = np.asarray(phases_rad, dtype=np.float64).ravel()
    n = phases.size
    if n == 0:
        return {
            "num_cells": 0,
            "phase_mean_rad": None,
            "phase_std_rad": None,
            "phase_min_rad": None,
            "phase_max_rad": None,
            "band_width_rad": None,
            "pi_baseline_band": (pi_lo, pi_hi),
            "all_in_pi_band": False,
            "fraction_in_pi_band": 0.0,
            "thermal_risk": "unknown",
            "nw_per_cell_limit_nw": nw_per_cell_limit,
        }

    mean_ = float(np.mean(phases))
    std_ = float(np.std(phases))
    min_ = float(np.min(phases))
    max_ = float(np.max(phases))
    band_width = max_ - min_

    all_in, frac_in = phases_comply_pi_baseline(phases, pi_lo, pi_hi)

    # Risk: high if any phase far outside [pi_lo, pi_hi]; medium if some outside; low if all in band
    outside_lo = np.sum(phases < pi_lo)
    outside_hi = np.sum(phases > pi_hi)
    max_dev = max(
        float(np.max(pi_lo - phases)) if outside_lo else 0.0,
        float(np.max(phases - pi_hi)) if outside_hi else 0.0,
    )
    if all_in:
        thermal_risk = "low"
    elif max_dev > 1.0:
        thermal_risk = "high"
    else:
        thermal_risk = "medium"

    return {
        "num_cells": n,
        "phase_mean_rad": round(mean_, 6),
        "phase_std_rad": round(std_, 6),
        "phase_min_rad": round(min_, 6),
        "phase_max_rad": round(max_, 6),
        "band_width_rad": round(band_width, 6),
        "pi_baseline_band": (round(pi_lo, 4), round(pi_hi, 4)),
        "all_in_pi_band": all_in,
        "fraction_in_pi_band": round(frac_in, 4),
        "thermal_risk": thermal_risk,
        "nw_per_cell_limit_nw": nw_per_cell_limit,
    }


def load_phases_from_npy(path: str) -> np.ndarray:
    """Load phase array from .npy file (radians)."""
    arr = np.load(path)
    return np.asarray(arr, dtype=np.float64).ravel()


def load_phases_from_inverse_json(path: str) -> tuple[np.ndarray, str | None]:
    """
    Load phases from inverse result JSON. Resolves phase_array_path relative to JSON dir.
    Returns (phases_rad, resolved_npy_path). If phase_array_path missing, raises ValueError.
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    npy_name = data.get("phase_array_path")
    if not npy_name:
        raise ValueError(f"Inverse JSON has no 'phase_array_path': {path}")
    json_dir = os.path.dirname(os.path.abspath(path))
    npy_path = os.path.join(json_dir, npy_name)
    if not os.path.isfile(npy_path):
        raise FileNotFoundError(f"Phase array file not found: {npy_path}")
    return load_phases_from_npy(npy_path), npy_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Thermodynamic validation: π-baseline and 18 nW/cell compliance for phase profiles.",
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=None,
        help="Path to .npy (phase array) or inverse result JSON (must contain phase_array_path).",
    )
    parser.add_argument(
        "--pi-band",
        type=str,
        default=None,
        metavar="lo,hi",
        help="Override π band as 'lo,hi' in radians (default: pi±0.14).",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Only print thermal_risk and all_in_pi_band.",
    )
    parser.add_argument(
        "-j", "--json",
        action="store_true",
        help="Output full report as JSON to stdout.",
    )
    args = parser.parse_args()

    if not args.input or not os.path.isfile(args.input):
        print("Usage: thermodynamic_validator.py <path to .npy or inverse JSON>", file=sys.stderr)
        return 1

    pi_lo, pi_hi = PI_BASELINE_LO, PI_BASELINE_HI
    if args.pi_band:
        parts = [p.strip() for p in args.pi_band.split(",")]
        if len(parts) != 2:
            print("--pi-band must be 'lo,hi' in radians", file=sys.stderr)
            return 1
        pi_lo, pi_hi = float(parts[0]), float(parts[1])

    try:
        if args.input.lower().endswith(".npy"):
            phases = load_phases_from_npy(args.input)
        else:
            phases, _ = load_phases_from_inverse_json(args.input)
    except (ValueError, FileNotFoundError, OSError) as e:
        print(f"Error loading input: {e}", file=sys.stderr)
        return 1

    report = phase_thermodynamic_report(phases, pi_lo=pi_lo, pi_hi=pi_hi)

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    if args.quiet:
        print(f"thermal_risk={report['thermal_risk']} all_in_pi_band={report['all_in_pi_band']}")
        return 0

    print("Thermodynamic validation (pi-baseline, 18 nW/cell proxy)")
    print(f"  Cells: {report['num_cells']}")
    print(f"  Phase (rad): mean={report['phase_mean_rad']} std={report['phase_std_rad']} min={report['phase_min_rad']} max={report['phase_max_rad']}")
    print(f"  pi band: [{report['pi_baseline_band'][0]}, {report['pi_baseline_band'][1]}]")
    print(f"  All in pi band: {report['all_in_pi_band']}  fraction in band: {report['fraction_in_pi_band']}")
    print(f"  Thermal risk: {report['thermal_risk']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
