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

try:
    from config.logger import get_logger
    log = get_logger(__name__)
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    _stdlog = logging.getLogger(__name__)
    class _LogAdapter:
        @staticmethod
        def info(msg, *args):
            if args:
                _stdlog.info(msg.replace("{}", "%s"), *args)
            else:
                _stdlog.info(msg)
        @staticmethod
        def error(msg, *args):
            if args:
                _stdlog.error(msg.replace("{}", "%s"), *args)
            else:
                _stdlog.error(msg)
    log = _LogAdapter()


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
        "--qubits",
        type=int,
        default=None,
        metavar="N",
        help="Number of logical qubits for standalone routing (required when not using a circuit). When pipeline is run with an OpenQASM circuit, topology and qubit count are derived from the circuit.",
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
    parser.add_argument(
        "--pdk",
        action="store_true",
        help="Use PDK config for GDS export (layer numbers, design rules). Requires --heac.",
    )
    parser.add_argument(
        "--pdk-config",
        type=str,
        default=None,
        help="Path to PDK config YAML; default: engineering/heac/pdk_config.yaml when --pdk.",
    )
    parser.add_argument(
        "--gds",
        action="store_true",
        help="After HEaC manifest, run manifest_to_gds to produce .gds (requires gdsfactory).",
    )
    parser.add_argument(
        "--drc",
        action="store_true",
        help="After GDS, run DRC (KLayout or mock). Implies --gds.",
    )
    parser.add_argument(
        "--lvs",
        action="store_true",
        help="After GDS, run LVS (schematic from manifest vs layout). Implies --gds.",
    )
    parser.add_argument(
        "--thermal",
        action="store_true",
        help="After inverse design, run thermal stage report (routing + phases -> thermal_report.json).",
    )
    parser.add_argument(
        "--parasitic",
        action="store_true",
        help="After HEaC manifest, run parasitic extraction (manifest -> decoherence_from_layout.json).",
    )
    parser.add_argument(
        "--dft",
        action="store_true",
        help="After HEaC manifest->GDS, run DFT script (padframes, alignment marks, witnesses) and merge into GDS.",
    )
    parser.add_argument(
        "--meep-verify",
        action="store_true",
        help="After HEaC manifest (or GDS), run MEEP verification and write S-param summary (optional; continues if Meep not installed).",
    )
    parser.add_argument(
        "--packaging",
        action="store_true",
        help="After HEaC manifest, run 2D→3D packaging (sample holder STEP). Requires CadQuery or build123d.",
    )
    parser.add_argument(
        "--use-orchestrator",
        action="store_true",
        help="Run pipeline as a Prefect DAG (retry failed nodes only; requires prefect).",
    )
    args = parser.parse_args()

    if not args.skip_routing and args.qubits is None:
        parser.error(
            "--qubits N is required when running routing without a circuit. "
            "Provide an OpenQASM circuit (circuit-driven pipeline) to derive topology and qubit count from the circuit, or specify --qubits N for standalone routing."
        )

    # Resolve paths from repo root or cwd
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)

    # Optional: run via Prefect DAG (retriable tasks)
    if getattr(args, "use_orchestrator", False) or os.environ.get("PREFECT_ORCHESTRATOR", "").strip() in ("1", "true", "yes"):
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))
        try:
            from orchestration import pipeline_flow, PipelineParams
            params = PipelineParams(
                output_base=args.output,
                device=args.device,
                model=args.model,
                routing_method=args.routing_method,
                skip_routing=args.skip_routing,
                skip_inverse=args.skip_inverse,
                fast=args.fast,
                hardware=args.hardware,
                with_superscreen=args.with_superscreen,
                heac=args.heac,
                heac_library=args.heac_library,
                pdk=args.pdk,
                pdk_config=args.pdk_config,
                gds=args.gds,
                drc=args.drc,
                lvs=args.lvs,
                dft=args.dft,
                thermal=args.thermal,
                parasitic=args.parasitic,
                meep_verify=args.meep_verify,
                packaging=args.packaging,
                num_qubits=args.qubits,
                script_dir=script_dir,
                repo_root=repo_root,
            )
            pipeline_flow(params)
            return 0
        except Exception as e:
            log.error("Orchestrator run failed: {}", str(e))
            return 1
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
                "--qubits", str(args.qubits),
            ]
            log.info("Running routing (RL local search)...")
        else:
            routing_cmd = [
                sys.executable,
                os.path.join(script_dir, "routing_qubo_qaoa.py"),
                "-o", routing_json,
                "--qubits", str(args.qubits),
            ]
            if args.hardware:
                routing_cmd.append("--hardware")
            if args.fast:
                routing_cmd.append("--fast")
            log.info("Running routing (QUBO/QAOA)...")
        rc = subprocess.run(routing_cmd, cwd=repo_root)
        if rc.returncode != 0:
            log.error("Routing failed.")
            return rc.returncode
        if not os.path.isfile(routing_json):
            log.error("Routing did not produce expected output file.")
            return 1
    else:
        if not os.path.isfile(routing_json):
            log.error("Skip-routing requested but {} not found.", routing_json)
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
            log.info("SuperScreen inductance: {}", inductance_json)
        else:
            log.info("SuperScreen step skipped (not installed or failed).")

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
        log.info("Running inverse design (topology -> phase profile)...")
        rc = subprocess.run(inverse_cmd, cwd=repo_root)
        if rc.returncode != 0:
            log.error("Inverse design failed.")
            return rc.returncode
    else:
        log.info("Skipping inverse design (--skip-inverse).")

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
            log.info("HEaC: no meta-atom library found; generating synthetic library...")
            heac_sweep = [
                sys.executable,
                os.path.join(script_dir, "heac", "meep_unit_cell_sweep.py"),
                "--no-meep", "-o", heac_library, "--points", "11",
            ]
            rc_heac = subprocess.run(heac_sweep, cwd=repo_root)
            if rc_heac.returncode != 0:
                log.error("HEaC: synthetic library generation failed.")
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
            log.info("Running HEaC phases -> geometry manifest...")
            rc_heac = subprocess.run(heac_cmd, cwd=repo_root)
            if rc_heac.returncode != 0:
                log.error("HEaC step failed.")
            else:
                log.info("  Geometry manifest: {}", manifest_path)

    # Optional: GDS export and DRC/LVS (require manifest from --heac)
    do_gds = args.gds or args.drc or args.lvs
    manifest_path = os.path.join(script_dir, args.output + "_geometry_manifest.json")
    if do_gds and os.path.isfile(manifest_path):
        gds_path = os.path.join(script_dir, args.output + ".gds")
        pdk_cfg = args.pdk_config or (os.path.join(script_dir, "heac", "pdk_config.yaml") if args.pdk else None)
        heac_dir = os.path.join(script_dir, "heac")
        # manifest_to_gds
        gds_cmd = [
            sys.executable,
            os.path.join(heac_dir, "manifest_to_gds.py"),
            manifest_path, "-o", gds_path,
        ]
        if pdk_cfg and os.path.isfile(pdk_cfg):
            gds_cmd += ["--pdk-config", pdk_cfg]
        log.info("Running manifest -> GDS...")
        rc_gds = subprocess.run(gds_cmd, cwd=repo_root)
        if rc_gds.returncode != 0:
            log.error("GDS export failed.")
            return rc_gds.returncode
        if not os.path.isfile(gds_path):
            log.info("GDS not produced (e.g. gdsfactory not installed); geometry manifest is sufficient for downstream tools.")
        else:
            log.info("  GDS: {}", gds_path)
        # DRC / LVS / DFT require GDS; skip when GDS was not produced (e.g. gdsfactory not installed)
        if os.path.isfile(gds_path) and args.drc:
            drc_report = os.path.join(script_dir, args.output + "_drc_report.json")
            rc_drc = subprocess.run(
                [sys.executable, os.path.join(heac_dir, "run_drc_klayout.py"), gds_path, "-o", drc_report],
                cwd=repo_root,
            )
            if rc_drc.returncode != 0:
                log.error("DRC failed.")
                return rc_drc.returncode
        if os.path.isfile(gds_path) and args.lvs:
            lvs_report = os.path.join(script_dir, args.output + "_lvs_report.json")
            lvs_cmd = [
                sys.executable, os.path.join(heac_dir, "run_lvs_klayout.py"),
                manifest_path, gds_path,
            ]
            if os.path.isfile(routing_json):
                lvs_cmd += ["--routing", routing_json]
            lvs_cmd += ["-o", lvs_report]
            rc_lvs = subprocess.run(lvs_cmd, cwd=repo_root)
            if rc_lvs.returncode != 0:
                log.error("LVS failed.")
                return rc_lvs.returncode
        if os.path.isfile(gds_path) and args.dft:
            dft_manifest_path = os.path.join(script_dir, args.output + "_dft_manifest.json")
            dft_cmd = [
                sys.executable,
                os.path.join(heac_dir, "dft_structures.py"),
                manifest_path,
                "-o", dft_manifest_path,
                "--merge", gds_path,
                "--output-gds", gds_path,
            ]
            if pdk_cfg and os.path.isfile(pdk_cfg):
                dft_cmd += ["--pdk-config", pdk_cfg]
            log.info("Running DFT (padframes, alignment, witnesses)...")
            rc_dft = subprocess.run(dft_cmd, cwd=repo_root)
            if rc_dft.returncode != 0:
                log.error("DFT merge failed.")
                return rc_dft.returncode
            log.info("  DFT merged into {}", gds_path)
    elif do_gds and not os.path.isfile(manifest_path):
        log.error("--gds/--drc/--lvs require HEaC manifest; run with --heac first.")
        return 1

    # Optional: thermal stage report (routing + phases)
    if args.thermal and os.path.isfile(routing_json):
        npy_thermal = os.path.join(script_dir, args.output + "_inverse_phases.npy")
        if not os.path.isfile(npy_thermal) and os.path.isfile(inverse_json):
            base_inv = os.path.splitext(inverse_json)[0]
            alt = base_inv + "_phases.npy"
            if os.path.isfile(alt):
                npy_thermal = alt
        if os.path.isfile(npy_thermal):
            thermal_report_path = os.path.join(script_dir, args.output + "_thermal_report.json")
            thermal_cmd = [
                sys.executable,
                os.path.join(script_dir, "thermal_stages.py"),
                routing_json, npy_thermal, "-o", thermal_report_path,
            ]
            log.info("Running thermal stage report...")
            rc_thermal = subprocess.run(thermal_cmd, cwd=repo_root)
            if rc_thermal.returncode != 0:
                log.error("Thermal report failed (check phase/routing inputs).")
            else:
                log.info("  Thermal report: {}", thermal_report_path)

    # Optional: MEEP verification (S-param summary; continues on failure if Meep not installed)
    if args.meep_verify:
        manifest_for_meep = os.path.join(script_dir, args.output + "_geometry_manifest.json")
        meep_summary_path = os.path.join(script_dir, args.output + "_meep_verify_summary.json")
        heac_lib = args.heac_library or os.path.join(script_dir, "meta_atom_library.json")
        meep_cmd = [
            sys.executable,
            os.path.join(script_dir, "meep_verify.py"),
            "-o", meep_summary_path,
        ]
        if os.path.isfile(manifest_for_meep):
            meep_cmd += ["--manifest", manifest_for_meep]
        if os.path.isfile(heac_lib):
            meep_cmd += ["--library", heac_lib]
        log.info("Running MEEP verification...")
        rc_meep = subprocess.run(meep_cmd, cwd=repo_root, capture_output=True, text=True, timeout=120)
        if rc_meep.returncode == 0:
            log.info("  MEEP summary: {}", meep_summary_path)
        else:
            log.info("  MEEP verification skipped or failed (Meep optional).")

    # Optional: 2D→3D packaging (STEP)
    if args.packaging:
        manifest_for_pkg = os.path.join(script_dir, args.output + "_geometry_manifest.json")
        if os.path.isfile(manifest_for_pkg):
            step_path = os.path.join(script_dir, args.output + "_sample_holder.step")
            pkg_cmd = [
                sys.executable,
                os.path.join(script_dir, "packaging", "cad_3d.py"),
                manifest_for_pkg, "-o", step_path,
            ]
            log.info("Running packaging (2D→3D STEP)...")
            rc_pkg = subprocess.run(pkg_cmd, cwd=repo_root, capture_output=True, text=True, timeout=60)
            if rc_pkg.returncode == 0:
                log.info("  STEP: {}", step_path)
            else:
                log.info("  Packaging skipped (CadQuery/build123d optional).")

    # Optional: parasitic extraction (manifest -> decoherence file)
    manifest_for_parasitic = os.path.join(script_dir, args.output + "_geometry_manifest.json")
    if args.parasitic and os.path.isfile(manifest_for_parasitic):
        decoherence_out = os.path.join(script_dir, args.output + "_decoherence_from_layout.json")
        parasitic_cmd = [
            sys.executable,
            os.path.join(script_dir, "parasitic_extraction.py"),
            manifest_for_parasitic,
        ]
        if os.path.isfile(routing_json):
            parasitic_cmd += ["--routing", routing_json]
        parasitic_cmd += ["-o", decoherence_out]
        log.info("Running parasitic extraction...")
        rc_parasitic = subprocess.run(parasitic_cmd, cwd=repo_root)
        if rc_parasitic.returncode != 0:
            log.error("Parasitic extraction failed.")
        else:
            log.info("  Decoherence from layout: {}", decoherence_out)

    log.info("Pipeline done. Outputs:")
    if os.path.isfile(routing_json):
        log.info("  Routing: {}", routing_json)
    if os.path.isfile(inductance_json):
        log.info("  Inductance: {}", inductance_json)
    if os.path.isfile(inverse_json):
        log.info("  Inverse: {}", inverse_json)
        if os.path.isfile(npy):
            log.info("  Phases:  {}", npy)
    return 0


if __name__ == "__main__":
    sys.exit(main())
