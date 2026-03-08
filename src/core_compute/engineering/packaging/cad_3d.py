"""
2D→3D CAD: read geometry manifest + packaging config, generate STEP for sample holder, RF puck, shielding.
Uses CadQuery or build123d when available. Ref: NEXT_STEPS_ROADMAP.md §5.1.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


def load_manifest(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def core_size_um(manifest: dict[str, Any]) -> tuple[float, float]:
    pitch = manifest.get("pitch_um", 1.0)
    shape = manifest.get("shape", [])
    if shape and len(shape) >= 2:
        ny, nx = int(shape[0]), int(shape[1])
        return (nx * pitch, ny * pitch)
    cells = manifest.get("cells", [])
    if not cells:
        return (pitch, pitch)
    max_i = max(c["i"] for c in cells)
    max_j = max(c["j"] for c in cells)
    return ((max_j + 1) * pitch, (max_i + 1) * pitch)


def build_sample_holder_step(
    core_width_um: float,
    core_height_um: float,
    cavity_margin_um: float = 500.0,
    output_path: str | None = None,
) -> str | None:
    """
    Generate sample holder STEP (cavity for die). Requires CadQuery or build123d.
    Returns path to written file or None if CAD lib not available.
    """
    try:
        import cadquery as cq
        w_mm = (core_width_um + 2 * cavity_margin_um) / 1000.0
        h_mm = (core_height_um + 2 * cavity_margin_um) / 1000.0
        depth_mm = 1.0
        box = cq.Workplane("XY").box(w_mm, h_mm, depth_mm)
        out = output_path or "sample_holder.step"
        box.val().exportStep(out)
        return out
    except ImportError:
        pass
    try:
        from build123d import BuildPart, Box, export_step
        w_mm = (core_width_um + 2 * cavity_margin_um) / 1000.0
        h_mm = (core_height_um + 2 * cavity_margin_um) / 1000.0
        depth_mm = 1.0
        with BuildPart() as part:
            Box(w_mm, h_mm, depth_mm)
        out = output_path or "sample_holder.step"
        export_step(part.part, out)
        return out
    except ImportError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate 3D STEP (sample holder, RF puck) from geometry manifest.",
    )
    parser.add_argument("manifest", help="Path to geometry_manifest.json")
    parser.add_argument("-o", "--output", default=None, help="Output STEP path (default: sample_holder.step)")
    parser.add_argument("--margin-um", type=float, default=500.0, help="Cavity margin around core (um)")
    args = parser.parse_args()

    if not os.path.isfile(args.manifest):
        print(f"Manifest not found: {args.manifest}", file=sys.stderr)
        return 1
    manifest = load_manifest(args.manifest)
    cw, ch = core_size_um(manifest)
    out_path = build_sample_holder_step(cw, ch, cavity_margin_um=args.margin_um, output_path=args.output)
    if out_path:
        print(f"Wrote {out_path}")
        return 0
    print("CadQuery/build123d not installed; install cadquery or build123d for STEP export.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
