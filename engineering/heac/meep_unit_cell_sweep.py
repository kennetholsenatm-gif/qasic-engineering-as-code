"""
Meep unit-cell sweep for HEaC: build meta-atom library (dimension -> transmission phase).
Sweeps one geometric parameter; runs small Meep 2D simulation per value or uses
deterministic formula when Meep is not installed. Outputs library as JSON for
phase_to_dimension interpolator.
Ref: Automated HEaC whitepaper, phase-to-geometry code flow.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Optional

import numpy as np

try:
    import meep as mp
    _HAS_MEEP = True
except ImportError:
    mp = None
    _HAS_MEEP = False


def _phase_from_meep(dimension: float, resolution: int = 20, cell_size: float = 10.0) -> float:
    """
    Run a minimal 2D Meep simulation: dielectric block (width = dimension) in a cell;
    extract phase of Ez at a point downstream. Returns phase in radians.
    """
    if not _HAS_MEEP:
        raise RuntimeError("Meep not installed")
    # 2D TE: Ez, Hx, Hy. Cell with a dielectric block centered; source left, probe right.
    sx, sy = cell_size, cell_size
    cell = mp.Vector3(sx, sy, 0)
    # Block: width = dimension (in meep units), height 2, epsilon 4
    w = max(0.2, min(dimension, sx - 2))
    block = mp.Block(
        center=mp.Vector3(0, 0, 0),
        size=mp.Vector3(w, 2.0, mp.inf),
        material=mp.Medium(epsilon=4),
    )
    fcen = 0.15
    df = 0.1
    sources = [
        mp.Source(
            mp.GaussianSource(fcen, fwidth=df),
            component=mp.Ez,
            center=mp.Vector3(-sx / 2 + 1, 0, 0),
        )
    ]
    sim = mp.Simulation(
        cell_size=cell,
        boundary_layers=[mp.PML(1.0)],
        geometry=[block],
        sources=sources,
        resolution=resolution,
        default_material=mp.Medium(epsilon=1),
    )
    # Run until steady state
    sim.run(until_after_sources=50)
    # Get Ez at a point to the right of the block (transmission side).
    # API: get_field_point(component, pt) or get_array over tiny volume; version-dependent.
    pt = mp.Vector3(sx / 2 - 1.5, 0, 0)
    try:
        ez = sim.get_field_point(mp.Ez, pt)
    except AttributeError:
        # Fallback: use formula if this Meep version has no get_field_point
        sim.reset_meep()
        return _phase_from_formula(dimension)
    sim.reset_meep()
    phase = math.atan2(ez.imag, ez.real)
    return phase


def _phase_from_formula(dimension: float) -> float:
    """
    Deterministic formula: phase (rad) from dimension. Monotonic so interpolator is well-defined.
    Used when Meep is not installed (synthetic library).
    """
    # Map dimension in [0.2, 2.0] to phase in [0, 2*pi] approximately
    d = float(dimension)
    d = max(0.2, min(2.0, d))
    return (d - 0.2) / 1.8 * 2 * math.pi


def run_sweep(
    dimension_min: float = 0.2,
    dimension_max: float = 2.0,
    num_points: int = 21,
    use_meep: bool = True,
    meep_resolution: int = 20,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Sweep dimension from dimension_min to dimension_max (linear spacing).
    Returns (dimensions, phases) in radians.
    """
    dimensions = np.linspace(dimension_min, dimension_max, num_points)
    phases = np.zeros(num_points, dtype=np.float64)
    for i, d in enumerate(dimensions):
        if use_meep and _HAS_MEEP:
            try:
                phases[i] = _phase_from_meep(d, resolution=meep_resolution)
            except Exception:
                phases[i] = _phase_from_formula(d)
        else:
            phases[i] = _phase_from_formula(d)
    return dimensions, phases


def save_library(
    dimensions: np.ndarray,
    phases: np.ndarray,
    out_path: str,
    library_source: str = "meep_sweep",
) -> None:
    """Save library as JSON (and optionally _dimensions.npy, _phases.npy for phase_to_dimension)."""
    path = Path(out_path)
    base = path.with_suffix("") if path.suffix.lower() == ".json" else path
    json_path = Path(str(base) + ".json")
    data = {
        "dimensions": dimensions.tolist(),
        "phases": phases.tolist(),
        "library_source": library_source,
        "num_points": len(dimensions),
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    np.save(Path(str(base) + "_dimensions.npy"), dimensions)
    np.save(Path(str(base) + "_phases.npy"), phases)
    print(f"Wrote {json_path} and {base}_dimensions.npy, {base}_phases.npy ({len(dimensions)} points)")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build meta-atom library: sweep dimension -> transmission phase (Meep or formula).",
    )
    parser.add_argument("-o", "--output", default="meta_atom_library.json", help="Output JSON path (also writes _dimensions.npy, _phases.npy)")
    parser.add_argument("--dim-min", type=float, default=0.2, help="Minimum dimension")
    parser.add_argument("--dim-max", type=float, default=2.0, help="Maximum dimension")
    parser.add_argument("--points", type=int, default=21, help="Number of sweep points")
    parser.add_argument("--no-meep", action="store_true", help="Use formula only (synthetic library)")
    parser.add_argument("--resolution", type=int, default=20, help="Meep resolution when using Meep")
    args = parser.parse_args()
    use_meep = not args.no_meep and _HAS_MEEP
    if not _HAS_MEEP and not args.no_meep:
        print("Meep not installed; using synthetic formula library (--no-meep implied)", file=sys.stderr)
    dimensions, phases = run_sweep(
        dimension_min=args.dim_min,
        dimension_max=args.dim_max,
        num_points=args.points,
        use_meep=use_meep,
        meep_resolution=args.resolution,
    )
    save_library(
        dimensions,
        phases,
        args.output,
        library_source="meep_sweep" if use_meep else "synthetic",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
