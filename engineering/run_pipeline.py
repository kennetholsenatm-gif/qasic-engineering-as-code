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
    parser.add_argument(
        "--heac",
        action="store_true",
        help="After inverse design, compile phases.npy to HEaC geometry manifest (requires meta-atom library).",
    )
    parser.add_argument(
        "--heac-library",
        type=str,
        default=None,
        help="Path to meta_atom_library.json for --heac; default: engineering/meta_atom_library.json (created with synthetic library if missing).",
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

    # Optional: HEaC phase-to-geometry (phases.npy -> geometry manifest)
    npy = os.path.join(script_dir, args.output + "_inverse_phases.npy")
    if not os.path.isfile(npy) and os.path.isfile(inverse_json):
        base_inv = os.path.splitext(inverse_json)[0]
        alt_npy = base_inv + "_phases.npy"
        if os.path.isfile(alt_npy):
            npy = alt_npy
    if args.heac and os.path.isfile(npy):
        heac_library = args.heac_library or os.path.join(script_dir, "meta_atom_library.json")
        if not os.path.isfile(heac_library):
            print("HEaC: no meta-atom library found; generating synthetic library...")
            heac_sweep = [
                sys.executable,
                os.path.join(script_dir, "heac", "meep_unit_cell_sweep.py"),
                "--no-meep", "-o", heac_library, "--points", "11",
            ]
            rc_heac = subprocess.run(heac_sweep, cwd=repo_root)
            if rc_heac.returncode != 0:
                print("HEaC: synthetic library generation failed.", file=sys.stderr)
        if os.path.isfile(heac_library):
            manifest_path = os.path.join(
                script_dir,
                args.output + "_geometry_manifest.json",
            )
            heac_cmd = [
                sys.executable,
                os.path.join(script_dir, "heac", "phases_to_geometry.py"),
                npy, "--library", heac_library, "-o", manifest_path,
                "--routing", routing_json,
            ]
            print("Running HEaC phases -> geometry manifest...")
            rc_heac = subprocess.run(heac_cmd, cwd=repo_root)
            if rc_heac.returncode != 0:
                print("HEaC step failed.", file=sys.stderr)
            else:
                print(f"  Geometry manifest: {manifest_path}")

    print("Pipeline done. Outputs:")
    if os.path.isfile(routing_json):
        print(f"  Routing: {routing_json}")
    if os.path.isfile(inductance_json):
        print(f"  Inductance: {inductance_json}")
    if os.path.isfile(inverse_json):
        print(f"  Inverse: {inverse_json}")
        if os.path.isfile(npy):
            print(f"  Phases:  {npy}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
