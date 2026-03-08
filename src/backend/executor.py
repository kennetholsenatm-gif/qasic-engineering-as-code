"""
DAG executor: topological run of nodes, resolve inputs from upstream outputs, dispatch to local or IBM QPU.
"""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.backend.dag_validate import is_acyclic
from src.backend.task_registry import (
    BACKEND_LOCAL,
    BACKEND_IBM_QPU,
    BACKEND_AWS_EKS,
    get_task_type,
)


def _topological_order(nodes: list[dict], edges: list[dict]) -> list[str]:
    """Return node ids in topological order. Assumes DAG is valid (acyclic)."""
    acyclic, _ = is_acyclic(nodes, edges)
    if not acyclic:
        return []
    node_ids = [n.get("id") for n in nodes if n.get("id")]
    in_degree = {nid: 0 for nid in node_ids}
    adj: dict[str, list[str]] = {nid: [] for nid in node_ids}
    for e in edges:
        src, tgt = e.get("source"), e.get("target")
        if src in in_degree and tgt in in_degree and src != tgt:
            in_degree[tgt] = in_degree.get(tgt, 0) + 1
            adj[src].append(tgt)
    queue = [nid for nid in node_ids if in_degree[nid] == 0]
    order = []
    while queue:
        u = queue.pop(0)
        order.append(u)
        for v in adj.get(u, []):
            in_degree[v] -= 1
            if in_degree[v] == 0:
                queue.append(v)
    return order


def _get_node_by_id(nodes: list[dict], node_id: str) -> dict | None:
    for n in nodes:
        if n.get("id") == node_id:
            return n
    return None


def _get_inputs_for_node(
    node_id: str,
    nodes: list[dict],
    edges: list[dict],
    node_outputs: dict[str, dict],
) -> dict[str, Any]:
    """Resolve input port -> value from incoming edges and upstream outputs."""
    inputs = {}
    for e in edges:
        if e.get("target") != node_id:
            continue
        src = e.get("source")
        out = node_outputs.get(src)
        if not out:
            continue
        target_handle = e.get("targetHandle")
        source_handle = e.get("sourceHandle")
        if source_handle and source_handle in out:
            key = target_handle or source_handle
            inputs[key] = out[source_handle]
        elif out:
            # Single output: use first key
            first_key = next(iter(out.keys()), None)
            if first_key:
                inputs[target_handle or first_key] = out[first_key]
    return inputs


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


def _execute_local(
    task_type: str,
    config: dict,
    inputs: dict,
    work_dir: Path,
) -> tuple[dict[str, Any], str | None]:
    """Execute task locally. Returns (outputs dict, error_message or None)."""
    engineering = REPO_ROOT / "src" / "core_compute" / "engineering"
    outputs = {}

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
        cmd = [
            sys.executable,
            str(engineering / "metasurface_inverse_net.py"),
            "--routing-result", routing_json,
            "--model", config.get("model", "mlp"),
            "--device", config.get("device", "auto"),
            "-o", str(out_json),
        ]
        code, _, err = _run_cmd(cmd, cwd=REPO_ROOT, timeout=600)
        if code != 0:
            return {}, err
        npy_path = work_dir / "inverse_phases.npy"
        if not npy_path.exists():
            npy_path = Path(str(out_json).replace(".json", "_phases.npy"))
        outputs["inverse_json"] = str(out_json)
        outputs["npy_path"] = str(npy_path) if npy_path.exists() else str(out_json)
        return outputs, None

    if task_type == "protocol_teleport":
        # Sim only in executor (blocking)
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


def _execute_ibm(task_type: str, config: dict, inputs: dict) -> tuple[dict[str, Any], str | None]:
    """Execute on IBM QPU where supported. Returns (outputs, error)."""
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
            outputs = {"result": result_dict}
            return outputs, None
        except Exception as e:
            return {}, str(e)

    if task_type == "routing":
        # Run routing with --hardware
        engineering = REPO_ROOT / "src" / "core_compute" / "engineering"
        work_dir = Path(tempfile.mkdtemp(prefix="qasic_dag_"))
        out_json = work_dir / "routing.json"
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
                shutil.rmtree(work_dir, ignore_errors=True)
            except Exception:
                pass

    return {}, f"IBM QPU not supported for task_type: {task_type}"


def run_dag(run_id: int, celery_task_id: str | None = None) -> dict[str, Any]:
    """
    Execute a DAG run: load run and snapshot, topo sort, run each node, store outputs.
    Updates dag_runs and dag_run_nodes. Returns summary dict.
    """
    from storage.db import (
        get_dag_run,
        update_dag_run,
        upsert_dag_run_node,
        is_enabled,
    )
    from datetime import datetime, timezone

    if not is_enabled():
        return {"success": False, "error": "Database not configured"}

    run = get_dag_run(run_id)
    if not run:
        return {"success": False, "error": "Run not found"}
    if run.get("status") not in ("pending", "running"):
        return {"success": False, "error": f"Run status is {run.get('status')}"}

    nodes = run.get("nodes_snapshot") or []
    edges = run.get("edges_snapshot") or []
    if not nodes:
        update_dag_run(run_id, status="failed", error_message="No nodes in DAG")
        return {"success": False, "error": "No nodes"}

    update_dag_run(run_id, status="running")
    order = _topological_order(nodes, edges)
    if len(order) != len(nodes):
        update_dag_run(run_id, status="failed", error_message="Graph has cycle")
        return {"success": False, "error": "Cycle detected"}

    work_dir = Path(tempfile.mkdtemp(prefix="qasic_dag_"))
    node_outputs: dict[str, dict] = {}
    now = datetime.now(timezone.utc)

    try:
        for node_id in order:
            node = _get_node_by_id(nodes, node_id)
            if not node:
                upsert_dag_run_node(run_id, node_id, status="failed", error_message="Node not found")
                continue

            data = node.get("data") or {}
            config = data.get("config") or {}
            task_type = data.get("task_type")
            if not task_type:
                upsert_dag_run_node(run_id, node_id, status="failed", error_message="Missing task_type")
                continue

            tt = get_task_type(task_type)
            if not tt:
                upsert_dag_run_node(run_id, node_id, status="failed", error_message=f"Unknown task_type: {task_type}")
                continue

            backend = config.get("backend", BACKEND_LOCAL)
            inputs = _get_inputs_for_node(node_id, nodes, edges, node_outputs)

            upsert_dag_run_node(run_id, node_id, status="running", started_at=now)

            if backend == BACKEND_LOCAL:
                outputs, err = _execute_local(task_type, config, inputs, work_dir)
            elif backend == BACKEND_IBM_QPU:
                outputs, err = _execute_ibm(task_type, config, inputs)
            elif backend == BACKEND_AWS_EKS:
                err = "EKS backend not configured"
                outputs = {}
            else:
                err = f"Unknown backend: {backend}"
                outputs = {}

            if err:
                upsert_dag_run_node(
                    run_id, node_id,
                    status="failed",
                    finished_at=datetime.now(timezone.utc),
                    error_message=err,
                )
                update_dag_run(
                    run_id,
                    status="failed",
                    finished_at=datetime.now(timezone.utc),
                    error_message=f"Node {node_id}: {err}",
                )
                return {"success": False, "failed_node": node_id, "error": err}
            node_outputs[node_id] = outputs
            upsert_dag_run_node(
                run_id, node_id,
                status="success",
                finished_at=datetime.now(timezone.utc),
                outputs=outputs,
            )

        update_dag_run(
            run_id,
            status="success",
            finished_at=datetime.now(timezone.utc),
        )
        return {"success": True, "run_id": run_id}
    finally:
        try:
            import shutil
            shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            pass
