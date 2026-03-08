"""
Local compute adapter: subprocess-based execution (routing, inverse, protocols, etc.).
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.backend.adapters.base import ComputeAdapter
from src.backend.task_registry import BACKEND_LOCAL


def _run_cmd(cmd: list[str], cwd: Path | None = None, timeout: int = 600) -> tuple[int, str, str]:
    import subprocess
    r = subprocess.run(
        cmd,
        cwd=cwd or REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


class LocalComputeAdapter(ComputeAdapter):
    """Execute tasks locally via subprocess (or Python API in Phase 5)."""

    def supports(self, task_type: str, backend: str) -> bool:
        return backend == BACKEND_LOCAL

    def execute(
        self,
        task_type: str,
        config: dict[str, Any],
        inputs: dict[str, Any],
        work_dir: Path,
    ) -> tuple[dict[str, Any], str | None]:
        engineering = REPO_ROOT / "src" / "core_compute" / "engineering"
        outputs: dict[str, Any] = {}

        if task_type == "routing":
            out_json = work_dir / "routing.json"
            use_rl = (config.get("routing_method") or "qaoa") == "rl"
            if use_rl:
                cmd = [sys.executable, str(engineering / "routing_rl.py"), "-o", str(out_json), "--qubits", "3"]
            else:
                cmd = [sys.executable, str(engineering / "routing_qubo_qaoa.py"), "-o", str(out_json)]
                if config.get("fast"):
                    cmd.append("--fast")
            code, _, err = _run_cmd(cmd, cwd=REPO_ROOT, timeout=300)
            if code != 0:
                return {}, err
            outputs["routing_json"] = str(out_json)
            return outputs, None

        if task_type == "inverse_design":
            routing_json = inputs.get("routing_json")
            if not routing_json or not os.path.isfile(routing_json):
                return {}, "Missing input routing_json"
            out_json = work_dir / "inverse.json"
            try:
                from src.core_compute.engineering.metasurface_inverse_net import run_inverse_design
                run_inverse_design(
                    routing_result_path=routing_json,
                    output_path=str(out_json),
                    device=config.get("device", "auto"),
                    model=config.get("model", "mlp"),
                )
            except Exception as e:
                return {}, str(e)
            npy_path = work_dir / "inverse_phases.npy"
            if not npy_path.exists():
                npy_path = Path(str(out_json).replace(".json", "_phases.npy"))
            outputs["inverse_json"] = str(out_json)
            outputs["npy_path"] = str(npy_path) if npy_path.exists() else str(out_json)
            return outputs, None

        if task_type == "protocol_teleport":
            with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
                out_path = f.name
            try:
                cmd = [sys.executable, str(engineering / "run_protocol_on_ibm.py"), "--protocol", "teleport", "-o", out_path]
                code, _, err = _run_cmd(cmd, cwd=REPO_ROOT, timeout=120)
                if code != 0:
                    return {}, err
                import json
                with open(out_path) as fp:
                    data = json.load(fp)
                outputs["result"] = data
                return outputs, None
            finally:
                if os.path.isfile(out_path):
                    try:
                        os.unlink(out_path)
                    except OSError:
                        pass

        if task_type == "protocol_bb84":
            try:
                from src.core_compute.protocols.qkd import run_bb84
                result = run_bb84(n_bits=config.get("n_bits", 64), seed=config.get("seed"))
                outputs["result"] = result
                return outputs, None
            except Exception as e:
                return {}, str(e)

        if task_type == "protocol_e91":
            try:
                from src.core_compute.protocols.qkd import run_e91
                result = run_e91(n_trials=config.get("n_trials", 500), seed=config.get("seed"))
                outputs["result"] = result
                return outputs, None
            except Exception as e:
                return {}, str(e)

        if task_type == "quantum_illumination":
            try:
                from src.core_compute.protocols.quantum_illumination import entangled_probe_metrics, unentangled_probe_metrics
                eta = max(0.0, min(1.0, config.get("eta", 0.1)))
                ent = entangled_probe_metrics(eta)
                unent = unentangled_probe_metrics(eta)
                outputs["result"] = {"eta": eta, "entangled": ent, "unentangled": unent}
                return outputs, None
            except Exception as e:
                return {}, str(e)

        if task_type == "quantum_radar":
            try:
                from src.core_compute.protocols.quantum_radar import run_quantum_radar
                out = run_quantum_radar(
                    eta=config.get("eta", 0.1),
                    n_b=max(0.0, config.get("n_b", 10.0)),
                    r=max(0.0, config.get("r", 0.5)),
                )
                outputs["result"] = out
                return outputs, None
            except Exception as e:
                return {}, str(e)

        return {}, f"Unsupported task_type for local: {task_type}"
