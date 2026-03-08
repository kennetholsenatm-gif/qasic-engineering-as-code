"""
Optional: compile HEaC geometry manifest to GDSII using gdsfactory.
If gdsfactory is not installed, exits with a clear message.
Ref: Automated HEaC whitepaper; gdsfactory for programmatic GDS layout.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Write geometry manifest to GDSII (requires gdsfactory).",
    )
    parser.add_argument("manifest", help="Path to geometry_manifest.json")
    parser.add_argument("-o", "--output", default=None, help="Output .gds path")
    parser.add_argument("--pitch-um", type=float, default=None, help="Override pitch from manifest (um)")
    args = parser.parse_args()

    try:
        import gdsfactory as gf
    except ImportError:
        print("gdsfactory not installed. Install with: pip install gdsfactory", file=sys.stderr)
        print("HEaC GDS export is optional; geometry manifest JSON is sufficient for downstream tools.", file=sys.stderr)
        return 1

    if not Path(args.manifest).exists():
        print(f"Manifest not found: {args.manifest}", file=sys.stderr)
        return 1
    with open(args.manifest, encoding="utf-8") as f:
        data = json.load(f)
    cells = data.get("cells", [])
    pitch_um = args.pitch_um if args.pitch_um is not None else data.get("pitch_um", 1.0)

    # Parameterized unit cell: rectangle with width = dimension (scaled), height = pitch_um
    @gf.cell
    def meta_atom(dimension_um: float, pitch_um: float = 1.0) -> gf.Component:
        c = gf.Component()
        w = dimension_um
        h = pitch_um * 0.8
        rect = gf.components.rectangle(size=(w, h), layer=(1, 0))
        c.add_ref(rect)
        return c

    # Top-level component: place one instance per cell
    top = gf.Component("metasurface")
    for cell in cells:
        i = cell["i"]
        j = cell["j"]
        dim = cell["dimension"]
        ref = meta_atom(dimension_um=dim, pitch_um=pitch_um)
        inst = top.add_ref(ref)
        inst.translate(j * pitch_um, i * pitch_um)
    out_path = args.output or str(Path(args.manifest).with_suffix(".gds"))
    top.write_gds(out_path)
    print(f"Wrote {out_path} ({len(cells)} cells)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
