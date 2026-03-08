"""
Pipeline executor: topological run of stages; runs OpenTofu, script, or waits for approval.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from . import storage


def _topological_order(nodes: list[dict], edges: list[dict]) -> list[str]:
    node_ids = [n.get("id") for n in nodes if n.get("id")]
    in_degree = {nid: 0 for nid in node_ids}
    adj: dict[str, list[str]] = {nid: [] for nid in node_ids}
    for e in edges:
        src, tgt = e.get("source"), e.get("target")
        if src in in_degree and tgt in in_degree and src != tgt:
            in_degree[tgt] = in_degree.get(tgt, 0) + 1
            adj.setdefault(src, []).append(tgt)
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


def _run_cmd(cmd: list[str], cwd: Path | None = None, env: dict | None = None) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            env=env or os.environ.copy(),
            capture_output=True,
            text=True,
            timeout=600,
        )
        return proc.returncode or 0, proc.stdout or "", proc.stderr or ""
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"
    except Exception as e:
        return -1, "", str(e)


def run_stage(
    run_id: int,
    node_id: str,
    stage_type: str,
    config: dict,
    repo_root: Path,
) -> None:
    """
    Execute a single stage and update run stage status in storage.
    """
    stage_data = {"status": "running", "stdout": "", "stderr": "", "exit_code": None, "output": {}}
    storage.update_run_stage(run_id, node_id, stage_data)

    if stage_type == "approval":
        storage.update_run_stage(run_id, node_id, {"status": "waiting_approval"})
        return

    if stage_type in ("tofu_init", "tofu_plan", "tofu_apply", "tofu_destroy"):
        tofu_root = (config.get("tofu_root") or "infra/tofu").strip()
        work_dir = (repo_root / tofu_root).resolve()
        if not work_dir.exists():
            storage.update_run_stage(
                run_id, node_id,
                {"status": "failed", "stderr": f"Tofu root not found: {work_dir}", "exit_code": -1},
            )
            return
        workspace = config.get("workspace")
        var_file = config.get("var_file")
        vars_dict = config.get("vars") or {}

        env = os.environ.copy()
        cmd_extra: list[str] = []
        if workspace:
            cmd_extra.extend(["-workspace", workspace])
        if var_file:
            cmd_extra.extend(["-var-file", var_file])
        for k, v in vars_dict.items():
            if v is None:
                continue
            cmd_extra.extend(["-var", f"{k}={v}"])

        if stage_type == "tofu_init":
            code, out, err = _run_cmd(["tofu", "init", "-input=false"], cwd=work_dir, env=env)
        elif stage_type == "tofu_plan":
            code, out, err = _run_cmd(["tofu", "plan", "-input=false", "-out=tfplan"] + cmd_extra, cwd=work_dir, env=env)
        elif stage_type == "tofu_apply":
            code, out, err = _run_cmd(["tofu", "apply", "-input=false", "-auto-approve", "tfplan"] + cmd_extra, cwd=work_dir, env=env)
            if code != 0 and "tfplan" in err:
                code, out, err = _run_cmd(["tofu", "apply", "-input=false", "-auto-approve"] + cmd_extra, cwd=work_dir, env=env)
        elif stage_type == "tofu_destroy":
            code, out, err = _run_cmd(["tofu", "destroy", "-input=false", "-auto-approve"] + cmd_extra, cwd=work_dir, env=env)
        else:
            code, out, err = -1, "", f"Unknown tofu stage: {stage_type}"

        status = "success" if code == 0 else "failed"
        storage.update_run_stage(run_id, node_id, {"status": status, "stdout": out, "stderr": err, "exit_code": code})
        return

    if stage_type == "script":
        script_path = config.get("script_path") or ""
        script_args = config.get("script_args") or []
        if not script_path:
            storage.update_run_stage(run_id, node_id, {"status": "failed", "stderr": "script_path not set", "exit_code": -1})
            return
        cmd = [script_path] + [str(a) for a in script_args]
        cwd = repo_root if repo_root.exists() else None
        code, out, err = _run_cmd(cmd, cwd=cwd)
        status = "success" if code == 0 else "failed"
        storage.update_run_stage(run_id, node_id, {"status": status, "stdout": out, "stderr": err, "exit_code": code})
        return

    storage.update_run_stage(run_id, node_id, {"status": "failed", "stderr": f"Unknown stage type: {stage_type}", "exit_code": -1})


def run_pipeline(run_id: int, repo_root: Path) -> None:
    """
    Run all stages of a pipeline in topological order. Updates run and stage status in storage.
    Approval stages block until approval is submitted via API (handled in main.py).
    """
    rec = storage.get_run(run_id)
    if not rec or rec.get("status") != "pending":
        return
    pipeline_id = rec["pipeline_id"]
    pipeline = storage.get_pipeline(pipeline_id)
    if not pipeline:
        storage.update_run(run_id, status="failed", message="Pipeline not found")
        return

    nodes = pipeline.get("nodes") or []
    edges = pipeline.get("edges") or []
    order = _topological_order(nodes, edges)
    if not order:
        storage.update_run(run_id, status="failed", message="Empty or invalid graph")
        return

    storage.update_run(run_id, status="running")
    stages = rec.get("stages") or {}
    for node_id in order:
        node = _get_node_by_id(nodes, node_id)
        if not node:
            continue
        data = node.get("data") or {}
        stage_type = data.get("stage_type") or "script"
        config = data.get("config") or {}

        current = stages.get(node_id) or {}
        if current.get("status") == "waiting_approval":
            continue
        if current.get("status") == "success":
            continue

        run_stage(run_id, node_id, stage_type, config, repo_root)
        updated = storage.get_run(run_id)
        stages = updated.get("stages") or {}
        stage_status = (stages.get(node_id) or {}).get("status", "failed")
        if stage_status == "failed":
            storage.update_run(run_id, status="failed", message=f"Stage {node_id} failed")
            return
        if stage_status == "waiting_approval":
            storage.update_run(run_id, status="running", message=f"Waiting for approval: {node_id}")
            return

    storage.update_run(run_id, status="success", message="Pipeline completed")
