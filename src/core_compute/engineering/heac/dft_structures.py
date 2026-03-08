"""
DFT (Design for Test): padframes, alignment marks, witness structures for HEaC tapeout.
Generates bond pads, alignment marks (crosses, frames), and witness structures
(standalone resonators, single JJs) from geometry manifest and PDK config.
Ref: NEXT_STEPS_ROADMAP.md §1.2 Automated DFT & Padframes.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

# Layer defaults when not in PDK: metal (1,0), pads (2,0), alignment (3,0), witness (4,0)
DFT_LAYER_PADS = (2, 0)
DFT_LAYER_ALIGNMENT = (3, 0)
DFT_LAYER_WITNESS = (4, 0)


def load_manifest(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_pdk_config(path: str | None) -> dict[str, Any] | None:
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
        return None
    except Exception:
        return None


def get_layer(pdk: dict[str, Any] | None, key: str, default: tuple[int, int]) -> tuple[int, int]:
    if not pdk or "layers" not in pdk or key not in pdk["layers"]:
        return default
    L = pdk["layers"][key]
    return (int(L[0]), int(L[1]))


def core_size_um(manifest: dict[str, Any], pitch_um: float | None = None) -> tuple[float, float]:
    """Return (width_um, height_um) of core from manifest shape and pitch."""
    pitch = pitch_um if pitch_um is not None else manifest.get("pitch_um", 1.0)
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


def build_padframe(
    core_width_um: float,
    core_height_um: float,
    pad_size_um: float = 80.0,
    pad_pitch_um: float = 100.0,
    margin_um: float = 50.0,
) -> list[dict[str, Any]]:
    """Generate padframe rectangles: ring of bond pads around core. Returns list of {x, y, w, h, layer_key}."""
    pads = []
    # Bounding box of pad ring (outside core)
    left = -margin_um - pad_size_um
    bottom = -margin_um - pad_size_um
    right = core_width_um + margin_um
    top = core_height_um + margin_um
    # Bottom row
    x = left
    while x < right + pad_pitch_um:
        pads.append({"x": x, "y": bottom, "w": pad_size_um, "h": pad_size_um, "layer_key": "pads"})
        x += pad_pitch_um
    # Top row
    x = left
    while x < right + pad_pitch_um:
        pads.append({"x": x, "y": top, "w": pad_size_um, "h": pad_size_um, "layer_key": "pads"})
        x += pad_pitch_um
    # Left column (exclude corners already)
    y = bottom + pad_pitch_um
    while y < top:
        pads.append({"x": left, "y": y, "w": pad_size_um, "h": pad_size_um, "layer_key": "pads"})
        y += pad_pitch_um
    # Right column
    y = bottom + pad_pitch_um
    while y < top:
        pads.append({"x": right, "y": y, "w": pad_size_um, "h": pad_size_um, "layer_key": "pads"})
        y += pad_pitch_um
    return pads


def build_alignment_marks(
    core_width_um: float,
    core_height_um: float,
    margin_um: float = 20.0,
    cross_size_um: float = 30.0,
    cross_width_um: float = 5.0,
) -> list[dict[str, Any]]:
    """Generate alignment marks at corners: crosses (two rects) and optional frame. Returns list of shapes."""
    shapes = []
    # Four corners (offset from core)
    positions = [
        (-margin_um - cross_size_um, -margin_um - cross_size_um),
        (core_width_um + margin_um, -margin_um - cross_size_um),
        (core_width_um + margin_um, core_height_um + margin_um),
        (-margin_um - cross_size_um, core_height_um + margin_um),
    ]
    for cx, cy in positions:
        # Cross: horizontal bar
        shapes.append({
            "type": "rect",
            "x": cx - cross_size_um / 2,
            "y": cy - cross_width_um / 2,
            "w": cross_size_um,
            "h": cross_width_um,
            "layer_key": "alignment",
        })
        # Cross: vertical bar
        shapes.append({
            "type": "rect",
            "x": cx - cross_width_um / 2,
            "y": cy - cross_size_um / 2,
            "w": cross_width_um,
            "h": cross_size_um,
            "layer_key": "alignment",
        })
    return shapes


def build_witness_structures(
    core_width_um: float,
    core_height_um: float,
    margin_um: float = 150.0,
    resonator_length_um: float = 200.0,
    resonator_width_um: float = 2.0,
    jj_size_um: float = 5.0,
) -> list[dict[str, Any]]:
    """Generate witness structures: standalone resonators (for Q extraction) and single JJ (for Ic, Rn)."""
    shapes = []
    # Place witnesses to the right of the chip
    base_x = core_width_um + margin_um
    base_y = 0.0
    # Standalone resonator: long narrow rectangle
    shapes.append({
        "type": "rect",
        "x": base_x,
        "y": base_y,
        "w": resonator_length_um,
        "h": resonator_width_um,
        "layer_key": "witness",
        "label": "resonator",
    })
    # Single JJ: small square
    shapes.append({
        "type": "rect",
        "x": base_x,
        "y": base_y + resonator_length_um * 0.5 + 20.0,
        "w": jj_size_um,
        "h": jj_size_um,
        "layer_key": "witness",
        "label": "single_jj",
    })
    return shapes


def build_dft_manifest(manifest_path: str, pdk_config_path: str | None) -> dict[str, Any]:
    """Build full DFT manifest (padframe, alignment, witnesses) from geometry manifest."""
    manifest = load_manifest(manifest_path)
    pdk = load_pdk_config(pdk_config_path)
    cw, ch = core_size_um(manifest)
    pads = build_padframe(cw, ch)
    alignment = build_alignment_marks(cw, ch)
    witnesses = build_witness_structures(cw, ch)
    return {
        "source": "dft_structures",
        "core_width_um": cw,
        "core_height_um": ch,
        "pads": pads,
        "alignment_marks": alignment,
        "witness_structures": witnesses,
        "manifest_ref": manifest_path,
    }


def add_dft_to_component_gds(
    gds_path: str,
    dft_manifest: dict[str, Any],
    output_gds_path: str,
    pdk: dict[str, Any] | None,
) -> int:
    """Merge DFT geometry into an existing GDS; write to output_gds_path. Requires gdsfactory."""
    try:
        import gdsfactory as gf
    except ImportError:
        print("gdsfactory required for GDS merge.", file=sys.stderr)
        return 1
    layer_metal = get_layer(pdk, "metal", (1, 0))
    layer_pads = get_layer(pdk, "pads", DFT_LAYER_PADS)
    layer_align = get_layer(pdk, "alignment", DFT_LAYER_ALIGNMENT)
    layer_witness = get_layer(pdk, "witness", DFT_LAYER_WITNESS)

    def layer_for(key: str) -> tuple[int, int]:
        if key == "pads":
            return layer_pads
        if key == "alignment":
            return layer_align
        if key == "witness":
            return layer_witness
        return layer_metal

    top = gf.import_gds(gds_path)
    for pad in dft_manifest.get("pads", []):
        rect = gf.components.rectangle(
            size=(pad["w"], pad["h"]),
            layer=layer_for(pad.get("layer_key", "pads")),
        )
        ref = top.add_ref(rect)
        ref.translate(pad["x"], pad["y"])
    for shape in dft_manifest.get("alignment_marks", []):
        rect = gf.components.rectangle(
            size=(shape["w"], shape["h"]),
            layer=layer_for(shape.get("layer_key", "alignment")),
        )
        ref = top.add_ref(rect)
        ref.translate(shape["x"], shape["y"])
    for shape in dft_manifest.get("witness_structures", []):
        rect = gf.components.rectangle(
            size=(shape["w"], shape["h"]),
            layer=layer_for(shape.get("layer_key", "witness")),
        )
        ref = top.add_ref(rect)
        ref.translate(shape["x"], shape["y"])
    top.write_gds(output_gds_path)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate DFT structures (padframes, alignment marks, witnesses) from HEaC manifest.",
    )
    parser.add_argument("manifest", help="Path to geometry_manifest.json")
    parser.add_argument("-o", "--output", default=None, help="Output DFT manifest JSON path")
    parser.add_argument("--pdk-config", default=None, help="Path to PDK config YAML")
    parser.add_argument(
        "--merge",
        metavar="GDS",
        default=None,
        help="Merge DFT into this GDS file and write --output-gds.",
    )
    parser.add_argument(
        "--output-gds",
        default=None,
        help="Output GDS path when using --merge.",
    )
    args = parser.parse_args()

    if not Path(args.manifest).exists():
        print(f"Manifest not found: {args.manifest}", file=sys.stderr)
        return 1

    dft = build_dft_manifest(args.manifest, args.pdk_config)
    out_json = args.output or str(Path(args.manifest).parent / "dft_manifest.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(dft, f, indent=2)
    print(f"Wrote {out_json}")

    if args.merge:
        if not args.output_gds:
            args.output_gds = args.merge
        pdk = load_pdk_config(args.pdk_config)
        rc = add_dft_to_component_gds(args.merge, dft, args.output_gds, pdk)
        if rc != 0:
            return rc
        print(f"Merged DFT into {args.output_gds}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
