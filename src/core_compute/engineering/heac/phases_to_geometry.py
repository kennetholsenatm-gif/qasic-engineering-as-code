"""
Phases.npy -> geometry manifest for HEaC. Load pipeline phase array, apply phase-to-dimension
interpolator from meta-atom library, output JSON manifest for downstream GDSII/CadQuery.
Ref: Automated HEaC whitepaper, phase-to-geometry code flow.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, Optional

# Allow running from repo root: python engineering/heac/phases_to_geometry.py
_this_dir = os.path.dirname(os.path.abspath(__file__))
_eng_dir = os.path.dirname(_this_dir)
_repo_root = os.path.dirname(_eng_dir)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

import numpy as np

try:
    from engineering.heac.phase_to_dimension import build_interpolator, phase_to_dimension
except ImportError:
    from heac.phase_to_dimension import build_interpolator, phase_to_dimension


def load_phases(path: str) -> np.ndarray:
    """Load phase array from .npy; return 2D array (N, M) or flatten to grid."""
    arr = np.load(path)
    arr = np.asarray(arr, dtype=np.float64)
    if arr.ndim == 1:
        n = int(np.sqrt(arr.size))
        if n * n != arr.size:
            return arr.reshape(1, -1)
        return arr.reshape(n, n)
    return arr


def build_manifest(
    phases: np.ndarray,
    interpolator: Callable[[float], float],
    pitch_um: float = 1.0,
    units: str = "um",
    library_source: str = "",
) -> dict[str, Any]:
    """Build geometry manifest dict: list of cells with i, j, phase_rad, dimension + global keys."""
    ny, nx = phases.shape
    cells = []
    for i in range(ny):
        for j in range(nx):
            phi = float(phases[i, j])
            d = interpolator(phi)
            cells.append({
                "i": i,
                "j": j,
                "phase_rad": round(phi, 6),
                "dimension": round(d, 6),
            })
    return {
        "pitch_um": pitch_um,
        "units": units,
        "library_source": library_source,
        "shape": [ny, nx],
        "num_cells": len(cells),
        "cells": cells,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compile phases.npy to geometry manifest using meta-atom library.",
    )
    parser.add_argument("phases_npy", help="Path to phases array (.npy)")
    parser.add_argument("--library", "-l", required=True, help="Path to meta_atom_library.json")
    parser.add_argument("-o", "--output", default=None, help="Output manifest JSON path")
    parser.add_argument("--routing", default=None, help="Optional routing.json for metadata (not yet embedded)")
    parser.add_argument("--pitch", type=float, default=1.0, help="Cell pitch in um")
    args = parser.parse_args()

    if not os.path.isfile(args.phases_npy):
        print(f"File not found: {args.phases_npy}", file=sys.stderr)
        return 1

    try:
        phases = load_phases(args.phases_npy)
    except Exception as e:
        print(f"Error loading phases: {e}", file=sys.stderr)
        return 1
    try:
        interp = build_interpolator(args.library)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error loading library: {e}", file=sys.stderr)
        return 1

    library_source = args.library
    manifest = build_manifest(phases, interp, pitch_um=args.pitch, library_source=library_source)
    if args.routing and os.path.isfile(args.routing):
        manifest["routing_ref"] = args.routing

    out_path = args.output or (Path(args.phases_npy).stem + "_geometry_manifest.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Wrote {manifest['num_cells']} cells to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
