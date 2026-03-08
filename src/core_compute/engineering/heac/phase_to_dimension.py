"""
Phase-to-dimension interpolator for HEaC: load meta-atom library (dimension -> phase)
and build a callable that maps desired phase (rad) to physical dimension.
Ref: Automated HEaC whitepaper, phase-to-geometry code flow.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable

import numpy as np
from scipy.interpolate import interp1d


def load_library(library_path: str) -> tuple[np.ndarray, np.ndarray]:
    """
    Load meta-atom library from JSON or from base_dimensions.npy + base_phases.npy.
    JSON format: {"dimensions": [...], "phases": [...]} in radians.
    Returns (dimensions, phases) as 1D arrays.
    """
    path = Path(library_path)
    if path.suffix.lower() == ".json" and path.exists():
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        dims = np.asarray(data["dimensions"], dtype=np.float64)
        phases = np.asarray(data["phases"], dtype=np.float64)
        return dims, phases
    base = path.with_suffix("")
    dim_path = Path(str(base) + "_dimensions.npy")
    phase_path = Path(str(base) + "_phases.npy")
    if dim_path.exists() and phase_path.exists():
        return np.load(dim_path), np.load(phase_path)
    raise FileNotFoundError(
        f"Meta-atom library not found: {library_path} or {dim_path} / {phase_path}"
    )


def build_interpolator(
    library_path: str,
    kind: str = "linear",
    fill_value: str | float | tuple[float, float] = "extrapolate",
) -> Callable[[float], float]:
    """
    Build interpolator mapping phase (rad) -> dimension from library file.
    Library must contain (dimensions, phases); we interpolate phases -> dimensions
    so that phase_to_dimension(phi) returns the dimension giving that phase.
    """
    dimensions, phases = load_library(library_path)
    if phases.size < 2:
        raise ValueError("Library must have at least 2 (dimension, phase) points")
    # Sort by phase for interp1d
    order = np.argsort(phases)
    phases_sorted = phases[order]
    dimensions_sorted = dimensions[order]
    interp = interp1d(
        phases_sorted,
        dimensions_sorted,
        kind=kind,
        fill_value=fill_value,
        bounds_error=False,
    )
    return lambda phi_rad: float(interp(float(phi_rad)))


def phase_to_dimension(phi_rad: float, interpolator: Callable[[float], float]) -> float:
    """Return physical dimension (same units as library) for desired phase in radians."""
    return interpolator(phi_rad)


def main() -> int:
    import argparse
    import math
    parser = argparse.ArgumentParser(
        description="Load meta-atom library and print interpolator(pi) or small table.",
    )
    parser.add_argument("library", help="Path to meta_atom_library.json (or base for .npy pair)")
    parser.add_argument("--table", action="store_true", help="Print phase -> dimension table for 0, pi/2, pi, 3pi/2, 2pi")
    args = parser.parse_args()
    try:
        interp = build_interpolator(args.library)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    if args.table:
        for phi in [0, math.pi / 2, math.pi, 3 * math.pi / 2, 2 * math.pi]:
            d = phase_to_dimension(phi, interp)
            print(f"  phase={phi:.4f} rad -> dimension={d:.6f}")
    else:
        d_pi = phase_to_dimension(math.pi, interp)
        print(f"interpolator(pi) = {d_pi:.6f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
