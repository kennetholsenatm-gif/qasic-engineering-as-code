"""
Map physical layout + noise model to Stim circuit; run syndrome extraction; predicted LER.
Ref: NEXT_STEPS_ROADMAP.md §8.4 QEC Decoder Integration (Stim / PyMatching).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def hardware_noise_to_stim_circuit(
    noise_nodes: list[dict[str, Any]],
    topology: str = "surface_code",
    distance: int = 3,
) -> dict[str, Any]:
    """
    Build Stim-style circuit description from per-node noise (gamma1, gamma2).
    Returns dict with circuit repr and optional LER placeholder.
    """
    # Stub: real implementation would use stim or pymatching
    try:
        import stim
        # Placeholder: build minimal circuit for surface code
        c = stim.Circuit()
        for _ in range(distance * distance):
            c.append("H", [0])
        return {"stim_available": True, "circuit_rounds": distance * distance, "ler_placeholder": 1e-4}
    except ImportError:
        return {"stim_available": False, "ler_placeholder": 1e-3, "message": "Stim not installed"}


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Map hardware noise to Stim circuit; output LER (stub).")
    parser.add_argument("decoherence_json", help="Path to decoherence or kinetic_inductance JSON")
    parser.add_argument("-o", "--output", default=None, help="Output report JSON")
    parser.add_argument("--distance", type=int, default=3, help="Surface code distance")
    args = parser.parse_args()
    with open(args.decoherence_json, encoding="utf-8") as f:
        data = json.load(f)
    nodes = data.get("nodes", [])
    out = hardware_noise_to_stim_circuit(nodes, distance=args.distance)
    if args.output:
        Path(args.output).write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
