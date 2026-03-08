"""
IBM Quantum adapter: execute protocol_teleport and routing --hardware on IBM QPU.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.backend.adapters.base import ComputeAdapter
from src.backend.task_registry import BACKEND_IBM_QPU


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


class IBMQuantumAdapter(ComputeAdapter):
    """Execute supported tasks on IBM QPU."""

    def supports(self, task_type: str, backend: str) -> bool:
        return backend == BACKEND_IBM_QPU

    def execute(
        self,
        task_type: str,
        config: dict[str, Any],
        inputs: dict[str, Any],
        work_dir: Path,
    ) -> tuple[dict[str, Any], str | None]:
        if task_type == "protocol_teleport":
            try:
                from src.core_compute.engineering.run_protocol_on_ibm import submit_protocol_job, get_job_status_and_result
                job_id, job, backend_name = submit_protocol_job("teleport", shots=1024)
                while True:
                    status_str, result_dict = get_job_status_and_result(job)
                    if status_str in ("DONE", "ERROR"):
                        break
                    import time
                    time.sleep(2)
                if status_str != "DONE":
                    return {}, result_dict.get("error") or status_str
                return {"result": result_dict}, None
            except Exception as e:
                return {}, str(e)

        if task_type == "routing":
            engineering = REPO_ROOT / "src" / "core_compute" / "engineering"
            work_dir_ibm = Path(tempfile.mkdtemp(prefix="qasic_dag_"))
            out_json = work_dir_ibm / "routing.json"
            try:
                cmd = [sys.executable, str(engineering / "routing_qubo_qaoa.py"), "-o", str(out_json), "--hardware"]
                if config.get("fast"):
                    cmd.append("--fast")
                code, _, err = _run_cmd(cmd, cwd=REPO_ROOT, timeout=600)
                if code != 0:
                    return {}, err
                return {"routing_json": str(out_json)}, None
            finally:
                try:
                    import shutil
                    shutil.rmtree(work_dir_ibm, ignore_errors=True)
                except Exception:
                    pass

        return {}, f"IBM QPU not supported for task_type: {task_type}"
