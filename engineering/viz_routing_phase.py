"""
Print a short summary of routing and/or inverse-design results. Loads routing JSON
and optionally phase array (.npy) or inverse result JSON. No physical metamaterials
required—for use after run_pipeline.py or manual routing/inverse runs.

Usage:
  python engineering/viz_routing_phase.py routing_result.json
  python engineering/viz_routing_phase.py routing_result.json inverse_result_phases.npy
  python engineering/viz_routing_phase.py pipeline_result_routing.json --inverse pipeline_result_inverse.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np


def load_json(path: str) -> dict:
    """Load JSON file; raise with clear message on missing file, invalid JSON, or I/O error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}") from e
    except OSError as e:
        raise OSError(f"Cannot read {path}: {e}") from e


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize routing and/or phase-array outputs.",
    )
    parser.add_argument(
        "routing_json",
        help="Path to routing JSON from routing_qubo_qaoa.py -o. Paths are relative to current working directory.",
    )
    parser.add_argument(
        "phases_npy",
        nargs="?",
        default=None,
        help="Optional path to phase array .npy from metasurface_inverse_net.py.",
    )
    parser.add_argument(
        "--inverse",
        default=None,
        metavar="INVERSE_JSON",
        help="Path to inverse result JSON; phase stats and phase_array_path are read from it. The .npy path is resolved relative to this file's directory unless phases_npy is given.",
    )
    parser.add_argument(
        "--histogram",
        action="store_true",
        help="Print a simple ASCII histogram of phase distribution.",
    )
    parser.add_argument(
        "--bins",
        type=int,
        default=12,
        help="Number of bins for histogram (default 12).",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.routing_json):
        print(f"File not found: {args.routing_json}", file=sys.stderr)
        return 1

    try:
        data = load_json(args.routing_json)
    except (FileNotFoundError, ValueError, OSError) as e:
        print(f"Error loading routing JSON: {e}", file=sys.stderr)
        return 1
    print("=== Routing ===")
    print(f"  Logical qubits: {data.get('num_logical_qubits', '?')}")
    print(f"  Physical nodes: {data.get('num_physical_nodes', '?')}")
    print(f"  Solver:         {data.get('solver', '?')}")
    print(f"  Objective:     {data.get('objective_value', '?')}")
    if data.get("backend"):
        print(f"  Backend:        {data['backend']}")
    mapping = data.get("mapping")
    if mapping:
        print("  Mapping (logical -> physical):")
        for m in mapping:
            print(f"    {m.get('logical')} -> {m.get('physical')}")
    print()

    phase_array = None
    if args.inverse and os.path.isfile(args.inverse):
        try:
            inv = load_json(args.inverse)
        except (FileNotFoundError, ValueError, OSError) as e:
            print(f"Error loading inverse JSON: {e}", file=sys.stderr)
            return 1
        print("=== Inverse design ===")
        print(f"  Device:     {inv.get('device', '?')}")
        print(f"  Meta-atoms: {inv.get('num_meta_atoms', '?')}")
        pmin = inv.get("phase_min")
        pmax = inv.get("phase_max")
        pmean = inv.get("phase_mean")
        pmin_s = f"{float(pmin):.3f}" if pmin is not None and isinstance(pmin, (int, float)) else "?"
        pmax_s = f"{float(pmax):.3f}" if pmax is not None and isinstance(pmax, (int, float)) else "?"
        pmean_s = f"{float(pmean):.3f}" if pmean is not None and isinstance(pmean, (int, float)) else "?"
        print(f"  Phase min:  {pmin_s} rad")
        print(f"  Phase max:  {pmax_s} rad")
        print(f"  Phase mean: {pmean_s} rad")
        phase_path = inv.get("phase_array_path")
        if phase_path and not args.phases_npy:
            base_dir = os.path.dirname(args.inverse)
            args.phases_npy = os.path.join(base_dir, phase_path)
        print()

    if args.phases_npy and os.path.isfile(args.phases_npy):
        phase_array = np.load(args.phases_npy)
    elif phase_array is None and args.phases_npy:
        print(f"Phase file not found: {args.phases_npy}", file=sys.stderr)
        return 1

    if phase_array is not None:
        if args.inverse is None or not os.path.isfile(args.inverse or ""):
            print("=== Phase array ===")
            print(f"  Shape: {phase_array.shape}")
            print(f"  Min:  {float(phase_array.min()):.3f} rad")
            print(f"  Max:  {float(phase_array.max()):.3f} rad")
            print(f"  Mean: {float(phase_array.mean()):.3f} rad")
            print()
        if args.histogram and phase_array.size > 0:
            hist, edges = np.histogram(phase_array.flatten(), bins=args.bins, range=(0, 2 * np.pi))
            max_count = max(hist) or 1
            print("=== Phase histogram (0 to 2*pi) ===")
            for i in range(len(hist)):
                bar_len = int(40 * hist[i] / max_count)
                print(f"  [{edges[i]:.2f}, {edges[i+1]:.2f}) |{'#' * bar_len} {hist[i]}")
            print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
