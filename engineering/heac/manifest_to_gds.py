"""
Optional: compile HEaC geometry manifest to GDSII using gdsfactory.
If gdsfactory is not installed, exits with a clear message.
Supports PDK config for layer numbers and design rules (min width, spacing).
Ref: Automated HEaC whitepaper; gdsfactory for programmatic GDS layout.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_pdk_config(path: str | None) -> dict[str, Any] | None:
    """Load PDK config from YAML or JSON; return None if path is None or file missing."""
    if not path or not Path(path).exists():
        return None
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    if Path(path).suffix.lower() == ".json":
        return json.loads(raw)
    try:
        import yaml
        return yaml.safe_load(raw)
    except ImportError:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None
    except Exception:
        return None


def get_layer(pdk: dict[str, Any] | None, key: str = "metal") -> tuple[int, int]:
    """Return (layer, datatype) from PDK or default (1, 0)."""
    if not pdk or "layers" not in pdk or key not in pdk["layers"]:
        return (1, 0)
    L = pdk["layers"][key]
    return (int(L[0]), int(L[1]))


def clamp_dimension(dim_um: float, pdk: dict[str, Any] | None) -> float:
    """Enforce min_width_um from PDK design_rules."""
    if not pdk or "design_rules" not in pdk:
        return dim_um
    min_w = pdk["design_rules"].get("min_width_um")
    if min_w is None:
        return dim_um
    return max(float(dim_um), float(min_w))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Write geometry manifest to GDSII (requires gdsfactory).",
    )
    parser.add_argument("manifest", help="Path to geometry_manifest.json")
    parser.add_argument("-o", "--output", default=None, help="Output .gds path")
    parser.add_argument("--pitch-um", type=float, default=None, help="Override pitch from manifest (um)")
    parser.add_argument(
        "--pdk-config",
        default=None,
        help="Path to PDK config YAML (layer numbers, design_rules). Default: no PDK (generic GDS).",
    )
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

    pdk = load_pdk_config(args.pdk_config)
    layer = get_layer(pdk)

    # Parameterized unit cell: rectangle with width = dimension (clamped to PDK min_width), height = pitch_um
    @gf.cell
    def meta_atom(dimension_um: float, pitch_um: float = 1.0, layer_tuple: tuple[int, int] = (1, 0)) -> gf.Component:
        c = gf.Component()
        w = clamp_dimension(dimension_um, pdk)
        h = max(pitch_um * 0.8, w * 0.5)  # keep aspect reasonable
        rect = gf.components.rectangle(size=(w, h), layer=layer_tuple)
        c.add_ref(rect)
        return c

    # Top-level component: place one instance per cell
    top = gf.Component("metasurface")
    for cell in cells:
        i = cell["i"]
        j = cell["j"]
        dim = cell["dimension"]
        ref = meta_atom(dimension_um=dim, pitch_um=pitch_um, layer_tuple=layer)
        inst = top.add_ref(ref)
        inst.translate(j * pitch_um, i * pitch_um)
    out_path = args.output or str(Path(args.manifest).with_suffix(".gds"))
    top.write_gds(out_path)
    print(f"Wrote {out_path} ({len(cells)} cells)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
