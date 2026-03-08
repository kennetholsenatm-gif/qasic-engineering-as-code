"""
Prefect tasks for each pipeline step. Each task is retriable independently.
"""
from __future__ import annotations

import os
import subprocess
import sys
from typing import Any

from .pipeline_params import PipelineParams

# Repo root for subprocess cwd (set by flow)
_REPO_ROOT: str = ""


def _run(cmd: list[str], cwd: str | None = None, timeout: int = 3600, capture: bool = False) -> tuple[int, str, str]:
    r = subprocess.run(
        cmd,
        cwd=cwd or _REPO_ROOT,
        capture_output=capture,
        text=True,
        timeout=timeout,
    )
    if capture:
        return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()
    return r.returncode, "", ""


def _ensure_npy_path(params: PipelineParams, inverse_json: str | None) -> str | None:
    npy = params.npy_path()
    if os.path.isfile(npy):
        return npy
    if inverse_json and os.path.isfile(inverse_json):
        base = os.path.splitext(inverse_json)[0]
        alt = base + "_phases.npy"
        if os.path.isfile(alt):
            return alt
    return None


def task_routing(params: PipelineParams) -> str:
    """Run routing (QAOA or RL). Returns path to routing_json."""
    if params.skip_routing:
        if not os.path.isfile(params.routing_json()):
            raise FileNotFoundError(f"Skip-routing requested but {params.routing_json()} not found.")
        return params.routing_json()
    script_dir = params.script_dir
    routing_json = params.routing_json()
    if params.routing_method == "rl":
        cmd = [sys.executable, os.path.join(script_dir, "routing_rl.py"), "-o", routing_json, "--qubits", "3"]
    else:
        cmd = [sys.executable, os.path.join(script_dir, "routing_qubo_qaoa.py"), "-o", routing_json]
        if params.hardware:
            cmd.append("--hardware")
        if params.fast:
            cmd.append("--fast")
    code, _, _ = _run(cmd)
    if code != 0:
        raise RuntimeError("Routing failed.")
    if not os.path.isfile(routing_json):
        raise RuntimeError("Routing did not produce expected output file.")
    return routing_json


def task_superscreen(params: PipelineParams, routing_json: str) -> str | None:
    """Optional SuperScreen inductance from routing. Returns inductance_json path or None."""
    if not params.with_superscreen or not os.path.isfile(routing_json):
        return None
    inductance_json = params.inductance_json()
    try:
        from src.core_compute.engineering.superscreen_demo import compute_inductance_from_routing
        ran = compute_inductance_from_routing(routing_json, inductance_json)
    except ImportError:
        try:
            from superscreen_demo import compute_inductance_from_routing
            ran = compute_inductance_from_routing(routing_json, inductance_json)
        except ImportError:
            return None
    return inductance_json if ran else None


def task_inverse_design(params: PipelineParams, routing_json: str) -> tuple[str, str]:
    """Run inverse design. Returns (inverse_json, npy_path)."""
    if params.skip_inverse:
        inv = params.inverse_json()
        npy = _ensure_npy_path(params, inv)
        if not os.path.isfile(inv) or not npy:
            raise FileNotFoundError("Skip-inverse requested but inverse output not found.")
        return inv, npy
    script_dir = params.script_dir
    inverse_json = params.inverse_json()
    cmd = [
        sys.executable,
        os.path.join(script_dir, "metasurface_inverse_net.py"),
        "--routing-result", routing_json,
        "--device", params.device,
        "--model", params.model,
        "-o", inverse_json,
    ]
    code, _, _ = _run(cmd)
    if code != 0:
        raise RuntimeError("Inverse design failed.")
    npy = _ensure_npy_path(params, inverse_json)
    if not npy:
        raise RuntimeError("Inverse design did not produce phases .npy")
    return inverse_json, npy


def task_heac_library(params: PipelineParams) -> str | None:
    """Generate synthetic meta-atom library if missing. Returns library path or None."""
    if not params.heac:
        return None
    script_dir = params.script_dir
    heac_library = params.heac_library or os.path.join(script_dir, "meta_atom_library.json")
    if os.path.isfile(heac_library):
        return heac_library
    sweep_cmd = [
        sys.executable,
        os.path.join(script_dir, "heac", "meep_unit_cell_sweep.py"),
        "--no-meep", "-o", heac_library, "--points", "11",
    ]
    code, _, _ = _run(sweep_cmd, timeout=600)
    if code != 0:
        raise RuntimeError("HEaC synthetic library generation failed.")
    return heac_library if os.path.isfile(heac_library) else None


def task_heac_phases_to_geometry(params: PipelineParams, routing_json: str, npy_path: str, heac_library: str | None) -> str | None:
    """HEaC phases -> geometry manifest. Returns manifest path or None."""
    if not params.heac or not npy_path or not os.path.isfile(npy_path):
        return None
    script_dir = params.script_dir
    lib = heac_library or params.heac_library or os.path.join(script_dir, "meta_atom_library.json")
    if not os.path.isfile(lib):
        return None
    manifest_path = params.manifest_path()
    cmd = [
        sys.executable,
        os.path.join(script_dir, "heac", "phases_to_geometry.py"),
        npy_path, "--library", lib, "-o", manifest_path,
        "--routing", routing_json,
    ]
    code, _, _ = _run(cmd)
    if code != 0:
        raise RuntimeError("HEaC phases -> geometry failed.")
    return manifest_path if os.path.isfile(manifest_path) else None


def task_manifest_to_gds(params: PipelineParams, manifest_path: str | None) -> str | None:
    """Manifest -> GDS. Returns gds_path or None."""
    if not (params.gds or params.drc or params.lvs):
        return None
    if not manifest_path or not os.path.isfile(manifest_path):
        raise FileNotFoundError("--gds/--drc/--lvs require HEaC manifest; run with --heac first.")
    script_dir = params.script_dir
    heac_dir = os.path.join(script_dir, "heac")
    gds_path = params.gds_path()
    pdk_cfg = params.pdk_config or (os.path.join(script_dir, "heac", "pdk_config.yaml") if params.pdk else None)
    cmd = [sys.executable, os.path.join(heac_dir, "manifest_to_gds.py"), manifest_path, "-o", gds_path]
    if pdk_cfg and os.path.isfile(pdk_cfg):
        cmd += ["--pdk-config", pdk_cfg]
    code, _, _ = _run(cmd)
    if code != 0:
        raise RuntimeError("GDS export failed.")
    if not os.path.isfile(gds_path):
        raise RuntimeError("GDS file not produced.")
    return gds_path


def task_drc(params: PipelineParams, gds_path: str | None) -> str | None:
    """Run DRC. Returns report path or None."""
    if not params.drc or not gds_path:
        return None
    script_dir = params.script_dir
    heac_dir = os.path.join(script_dir, "heac")
    drc_report = os.path.join(script_dir, f"{params.output_base}_drc_report.json")
    code, _, _ = _run([
        sys.executable, os.path.join(heac_dir, "run_drc_klayout.py"), gds_path, "-o", drc_report,
    ])
    if code != 0:
        raise RuntimeError("DRC failed.")
    return drc_report


def task_lvs(params: PipelineParams, manifest_path: str | None, gds_path: str | None, routing_json: str) -> str | None:
    """Run LVS. Returns report path or None."""
    if not params.lvs or not gds_path or not manifest_path:
        return None
    script_dir = params.script_dir
    heac_dir = os.path.join(script_dir, "heac")
    lvs_report = os.path.join(script_dir, f"{params.output_base}_lvs_report.json")
    cmd = [sys.executable, os.path.join(heac_dir, "run_lvs_klayout.py"), manifest_path, gds_path]
    if os.path.isfile(routing_json):
        cmd += ["--routing", routing_json]
    cmd += ["-o", lvs_report]
    code, _, _ = _run(cmd)
    if code != 0:
        raise RuntimeError("LVS failed.")
    return lvs_report


def task_dft(params: PipelineParams, manifest_path: str | None, gds_path: str | None) -> str | None:
    """DFT merge into GDS. Returns gds_path or None."""
    if not params.dft or not manifest_path or not gds_path:
        return None
    script_dir = params.script_dir
    heac_dir = os.path.join(script_dir, "heac")
    pdk_cfg = params.pdk_config or (os.path.join(script_dir, "heac", "pdk_config.yaml") if params.pdk else None)
    dft_manifest = os.path.join(script_dir, f"{params.output_base}_dft_manifest.json")
    cmd = [
        sys.executable, os.path.join(heac_dir, "dft_structures.py"),
        manifest_path, "-o", dft_manifest, "--merge", gds_path, "--output-gds", gds_path,
    ]
    if pdk_cfg and os.path.isfile(pdk_cfg):
        cmd += ["--pdk-config", pdk_cfg]
    code, _, _ = _run(cmd)
    if code != 0:
        raise RuntimeError("DFT merge failed.")
    return gds_path


def task_thermal(params: PipelineParams, routing_json: str, npy_path: str | None) -> str | None:
    """Thermal stage report. Returns report path or None."""
    if not params.thermal or not npy_path or not os.path.isfile(npy_path):
        return None
    script_dir = params.script_dir
    thermal_report = os.path.join(script_dir, f"{params.output_base}_thermal_report.json")
    code, _, _ = _run([
        sys.executable, os.path.join(script_dir, "thermal_stages.py"),
        routing_json, npy_path, "-o", thermal_report,
    ])
    if code != 0:
        raise RuntimeError("Thermal report failed.")
    return thermal_report if os.path.isfile(thermal_report) else None


def task_meep_verify(params: PipelineParams, manifest_path: str | None) -> str | None:
    """MEEP verification (optional; continues on failure). Returns summary path or None."""
    if not params.meep_verify:
        return None
    script_dir = params.script_dir
    meep_summary = os.path.join(script_dir, f"{params.output_base}_meep_verify_summary.json")
    heac_lib = params.heac_library or os.path.join(script_dir, "meta_atom_library.json")
    cmd = [sys.executable, os.path.join(script_dir, "meep_verify.py"), "-o", meep_summary]
    if manifest_path and os.path.isfile(manifest_path):
        cmd += ["--manifest", manifest_path]
    if os.path.isfile(heac_lib):
        cmd += ["--library", heac_lib]
    code, _, _ = _run(cmd, timeout=120, capture=True)
    return meep_summary if os.path.isfile(meep_summary) else None


def task_packaging(params: PipelineParams, manifest_path: str | None) -> str | None:
    """2D->3D STEP. Returns step path or None."""
    if not params.packaging or not manifest_path or not os.path.isfile(manifest_path):
        return None
    script_dir = params.script_dir
    step_path = os.path.join(script_dir, f"{params.output_base}_sample_holder.step")
    code, _, _ = _run([
        sys.executable, os.path.join(script_dir, "packaging", "cad_3d.py"), manifest_path, "-o", step_path,
    ], timeout=60, capture=True)
    return step_path if os.path.isfile(step_path) else None


def task_parasitic(params: PipelineParams, manifest_path: str | None, routing_json: str) -> str | None:
    """Parasitic extraction -> decoherence. Returns output path or None."""
    if not params.parasitic or not manifest_path or not os.path.isfile(manifest_path):
        return None
    script_dir = params.script_dir
    decoherence_out = os.path.join(script_dir, f"{params.output_base}_decoherence_from_layout.json")
    cmd = [sys.executable, os.path.join(script_dir, "parasitic_extraction.py"), manifest_path]
    if os.path.isfile(routing_json):
        cmd += ["--routing", routing_json]
    cmd += ["-o", decoherence_out]
    code, _, _ = _run(cmd)
    if code != 0:
        raise RuntimeError("Parasitic extraction failed.")
    return decoherence_out if os.path.isfile(decoherence_out) else None


def set_repo_root(root: str) -> None:
    global _REPO_ROOT
    _REPO_ROOT = root
