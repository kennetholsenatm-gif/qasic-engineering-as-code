"""
Run the full metasurface pipeline without physical hardware: routing (QUBO/QAOA)
then inverse design (topology -> phase profile). Uses simulation by default; optional
--hardware runs routing on real IBM Quantum. No physical metamaterials required.

Usage:
  python engineering/run_pipeline.py
  python engineering/run_pipeline.py --hardware
  python engineering/run_pipeline.py -o my_result
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run routing (QAOA) then inverse design; chain routing output into inverse net.",
    )
    parser.add_argument(
        "--hardware",
        action="store_true",
        help="Run routing on real IBM Quantum (requires IBM_QUANTUM_TOKEN); default is simulation.",
    )
    parser.add_argument(
        "-o", "--output",
        default="pipeline_result",
        help="Base name for outputs: <base>_routing.json, <base>_inverse.json, <base>_inverse_phases.npy (default: pipeline_result).",
    )
    parser.add_argument(
        "--device",
        default="auto",
        choices=("auto", "cpu", "cuda", "mps"),
        help="Device for inverse net: auto|cpu|cuda|mps (default: auto).",
    )
    parser.add_argument(
        "--skip-routing",
        action="store_true",
        help="Skip routing step; use existing <output>_routing.json (must exist).",
    )
    parser.add_argument(
        "--skip-inverse",
        action="store_true",
        help="Skip inverse-design step (only run routing).",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Pass --fast to routing (budget preset for affordable runs).",
    )
    parser.add_argument(
        "--with-superscreen",
        action="store_true",
        help="After routing, run SuperScreen to compute inductance from topology (optional; requires superscreen).",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="mlp",
        choices=("mlp", "gnn"),
        help="Inverse design model: mlp (default) or gnn.",
    )
    parser.add_argument(
        "--routing-method",
        type=str,
        default="qaoa",
        choices=("qaoa", "rl"),
        help="Routing method: qaoa (QUBO/QAOA) or rl (RL-style local search).",
    )
    args = parser.parse_args()

    # Resolve paths from repo root or cwd
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    routing_json = os.path.join(script_dir, args.output + "_routing.json")
    inverse_json = os.path.join(script_dir, args.output + "_inverse.json")
    inductance_json = os.path.join(script_dir, args.output + "_inductance.json")

    # Step 1: Routing
    if not args.skip_routing:
        if args.routing_method == "rl":
            routing_cmd = [
                sys.executable,
                os.path.join(script_dir, "routing_rl.py"),
                "-o", routing_json,
                "--qubits", "3",
            ]
            print("Running routing (RL local search)...")
        else:
            routing_cmd = [
                sys.executable,
                os.path.join(script_dir, "routing_qubo_qaoa.py"),
                "-o", routing_json,
            ]
            if args.hardware:
                routing_cmd.append("--hardware")
            if args.fast:
                routing_cmd.append("--fast")
            print("Running routing (QUBO/QAOA)...")
        rc = subprocess.run(routing_cmd, cwd=repo_root)
        if rc.returncode != 0:
            print("Routing failed.", file=sys.stderr)
            return rc.returncode
        if not os.path.isfile(routing_json):
            print("Routing did not produce expected output file.", file=sys.stderr)
            return 1
    else:
        if not os.path.isfile(routing_json):
            print(f"Skip-routing requested but {routing_json} not found.", file=sys.stderr)
            return 1

    # Optional: SuperScreen inductance from routing topology
    if args.with_superscreen and os.path.isfile(routing_json):
        try:
            from engineering.superscreen_demo import compute_inductance_from_routing
            ran = compute_inductance_from_routing(routing_json, inductance_json)
        except ImportError:
            try:
                from superscreen_demo import compute_inductance_from_routing
                ran = compute_inductance_from_routing(routing_json, inductance_json)
            except ImportError:
                ran = False
        if ran:
            print(f"SuperScreen inductance: {inductance_json}")
        else:
            print("SuperScreen step skipped (not installed or failed).")

    # Step 2: Inverse design
    if not args.skip_inverse:
        inverse_cmd = [
            sys.executable,
            os.path.join(script_dir, "metasurface_inverse_net.py"),
            "--routing-result", routing_json,
            "--device", args.device,
            "--model", args.model,
            "-o", inverse_json,
        ]
        print("Running inverse design (topology -> phase profile)...")
        rc = subprocess.run(inverse_cmd, cwd=repo_root)
        if rc.returncode != 0:
            print("Inverse design failed.", file=sys.stderr)
            return rc.returncode
    else:
        print("Skipping inverse design (--skip-inverse).")

    print("Pipeline done. Outputs:")
    if os.path.isfile(routing_json):
        print(f"  Routing: {routing_json}")
    if os.path.isfile(inductance_json):
        print(f"  Inductance: {inductance_json}")
    if os.path.isfile(inverse_json):
        print(f"  Inverse: {inverse_json}")
        npy = os.path.join(script_dir, args.output + "_inverse_phases.npy")
        if os.path.isfile(npy):
            print(f"  Phases:  {npy}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
