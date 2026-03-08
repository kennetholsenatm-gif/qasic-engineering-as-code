"""
Phase synthesis report: stats + thermodynamic validation (Graph-Theoretic Inverse Design whitepaper).
Input: inverse result JSON or phase array .npy. Output: human-readable report; optional JSON.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import numpy as np

try:
    from engineering.thermodynamic_validator import (
        load_phases_from_inverse_json,
        load_phases_from_npy,
        phase_thermodynamic_report,
        PI_BASELINE_LO,
        PI_BASELINE_HI,
    )
except ImportError:
    from thermodynamic_validator import (
        load_phases_from_inverse_json,
        load_phases_from_npy,
        phase_thermodynamic_report,
        PI_BASELINE_LO,
        PI_BASELINE_HI,
    )


def build_report(path: str, pi_lo: float, pi_hi: float) -> dict[str, Any]:
    """Load phases from path (.npy or inverse JSON) and return full report dict."""
    if path.lower().endswith(".npy"):
        phases = load_phases_from_npy(path)
        source = "npy"
        source_path = path
    else:
        phases, source_path = load_phases_from_inverse_json(path)
        source = "inverse_json"
    report = phase_thermodynamic_report(phases, pi_lo=pi_lo, pi_hi=pi_hi)
    report["source"] = source
    report["source_path"] = os.path.abspath(source_path)
    # Optional: suggest 3D viewer if frontend exists
    report["viewer_note"] = "Use Phase 3D viewer (dashboard) to visualize phase array."
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Phase synthesis report: stats and thermodynamic validation.",
    )
    parser.add_argument(
        "input",
        help="Path to inverse result JSON or phase array .npy.",
    )
    parser.add_argument(
        "--pi-band",
        type=str,
        default=None,
        metavar="lo,hi",
        help="π band as 'lo,hi' radians (default: pi±0.14).",
    )
    parser.add_argument(
        "-j", "--json",
        action="store_true",
        help="Output report as JSON only.",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"File not found: {args.input}", file=sys.stderr)
        return 1

    pi_lo, pi_hi = PI_BASELINE_LO, PI_BASELINE_HI
    if args.pi_band:
        parts = [p.strip() for p in args.pi_band.split(",")]
        if len(parts) != 2:
            print("--pi-band must be 'lo,hi' in radians", file=sys.stderr)
            return 1
        pi_lo, pi_hi = float(parts[0]), float(parts[1])

    try:
        report = build_report(args.input, pi_lo, pi_hi)
    except (ValueError, FileNotFoundError, OSError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print("=== Phase synthesis report ===")
    print(f"Source: {report['source_path']}")
    print(f"Cells: {report['num_cells']}")
    print(f"Phase (rad): mean={report['phase_mean_rad']}  std={report['phase_std_rad']}")
    print(f"Range: [{report['phase_min_rad']}, {report['phase_max_rad']}]  width={report['band_width_rad']}")
    print(f"pi-baseline band: {report['pi_baseline_band']}")
    print(f"In band: {report['all_in_pi_band']}  fraction={report['fraction_in_pi_band']}")
    print(f"Thermal risk: {report['thermal_risk']}")
    print(f"Note: {report['viewer_note']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
