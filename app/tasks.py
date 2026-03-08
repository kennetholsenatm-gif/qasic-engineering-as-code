"""
Celery tasks for heavy workloads: pipeline, MEEP unit-cell sweep, inverse design (GNN).
Keeps API/frontend responsive by offloading to workers.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

ENGINEERING_DIR = REPO_ROOT / "engineering"


def _run_cmd(cmd: list[str], cwd: Path | None = None, timeout: int = 3600) -> tuple[int, str, str]:
    r = subprocess.run(
        cmd,
        cwd=cwd or REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def _task_app():
    from app.celery_app import get_celery_app
    return get_celery_app()


app = _task_app()


@app.task(bind=True, name="qasic.run_pipeline")
def run_pipeline_task(self, output_base: str = "pipeline_result", fast: bool = False,
                     routing_method: str = "qaoa", model: str = "mlp", heac: bool = False,
                     skip_routing: bool = False, skip_inverse: bool = False,
                     hardware: bool = False):
    """Run full pipeline (routing + inverse + optional HEaC)."""
    cmd = [sys.executable, str(ENGINEERING_DIR / "run_pipeline.py"), "-o", output_base]
    if fast:
        cmd.append("--fast")
    if routing_method in ("qaoa", "rl"):
        cmd.extend(["--routing-method", routing_method])
    if model in ("mlp", "gnn"):
        cmd.extend(["--model", model])
    if heac:
        cmd.append("--heac")
    if skip_routing:
        cmd.append("--skip-routing")
    if skip_inverse:
        cmd.append("--skip-inverse")
    if hardware:
        cmd.append("--hardware")
    task_id = self.request.id if getattr(self.request, "id", None) else None
    code, out, err = _run_cmd(cmd, timeout=1800)
    routing_json = ENGINEERING_DIR / f"{output_base}_routing.json"
    inverse_json = ENGINEERING_DIR / f"{output_base}_inverse.json"
    if code != 0:
        try:
            from storage.db import update_pipeline_run
            update_pipeline_run(task_id=task_id, status="failed", error_message=err or out)
        except Exception:
            pass
        return {"success": False, "exit_code": code, "stderr": err, "stdout": out}
    try:
        from storage.db import update_pipeline_run
        update_pipeline_run(
            task_id=task_id,
            status="success",
            routing_path=str(routing_json) if routing_json.exists() else None,
            inverse_path=str(inverse_json) if inverse_json.exists() else None,
        )
    except Exception:
        pass
    result = {"success": True, "output_base": output_base}
    if routing_json.exists():
        try:
            with open(routing_json, encoding="utf-8") as f:
                result["routing"] = json.load(f)
        except (OSError, json.JSONDecodeError):
            pass
    if inverse_json.exists():
        try:
            with open(inverse_json, encoding="utf-8") as f:
                result["inverse"] = json.load(f)
        except (OSError, json.JSONDecodeError):
            pass
    return result


@app.task(bind=True, name="qasic.meep_sweep")
def meep_sweep_task(self, output_path: str | None = None, points: int = 21, no_meep: bool = False):
    """Run MEEP unit-cell sweep (meta-atom library)."""
    out = output_path or str(ENGINEERING_DIR / "meta_atom_library.json")
    cmd = [sys.executable, str(ENGINEERING_DIR / "heac" / "meep_unit_cell_sweep.py"),
           "-o", out, "--points", str(points)]
    if no_meep:
        cmd.append("--no-meep")
    code, stdout, stderr = _run_cmd(cmd, timeout=1200)
    if code != 0:
        return {"success": False, "exit_code": code, "stderr": stderr}
    result = {"success": True, "output_path": out}
    if os.path.isfile(out):
        try:
            with open(out, encoding="utf-8") as f:
                data = json.load(f)
            result["library_preview"] = list(data.keys()) if isinstance(data, dict) else []
        except Exception:
            pass
    return result


@app.task(bind=True, name="qasic.inverse_design")
def inverse_design_task(self, routing_result_path: str | None = None, model: str = "mlp",
                        device: str = "auto", output_base: str = "pipeline_result",
                        phase_band: str | None = None):
    """Run inverse design (MLP or GNN). Writes to <output_base>_inverse.json and _inverse_phases.npy for dashboard."""
    out_json = str(ENGINEERING_DIR / f"{output_base}_inverse.json")
    cmd = [sys.executable, str(ENGINEERING_DIR / "metasurface_inverse_net.py"),
           "-o", out_json, "--model", model, "--device", device]
    if routing_result_path and os.path.isfile(routing_result_path):
        cmd.extend(["--routing-result", routing_result_path])
    if phase_band:
        cmd.extend(["--phase-band", phase_band])
    code, stdout, stderr = _run_cmd(cmd, timeout=600)
    if code != 0:
        return {"success": False, "exit_code": code, "stderr": stderr}
    result = {"success": True, "output_json": out_json}
    if os.path.isfile(out_json):
        try:
            with open(out_json, encoding="utf-8") as f:
                result["inverse"] = json.load(f)
        except (OSError, json.JSONDecodeError):
            pass
    return result
