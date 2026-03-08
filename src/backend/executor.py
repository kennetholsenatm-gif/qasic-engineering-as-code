"""
DAG executor: topological run of nodes, resolve inputs from upstream outputs, dispatch to local or IBM QPU.
"""
from __future__ import annotations

import sys
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HEARTBEAT_INTERVAL_SECONDS = 10

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.backend.dag_validate import is_acyclic
from src.backend.task_registry import get_task_type
from src.backend.dispatcher import dispatch as dispatcher_dispatch


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


def _heartbeat_loop(run_id: int, stop_event: threading.Event) -> None:
    """Update last_heartbeat every HEARTBEAT_INTERVAL_SECONDS until stop_event is set."""
    from storage.db import update_dag_run_heartbeat
    while not stop_event.wait(timeout=HEARTBEAT_INTERVAL_SECONDS):
        update_dag_run_heartbeat(run_id)


def run_dag(run_id: int, celery_task_id: str | None = None, run_dag_node_task: Any = None) -> dict[str, Any]:
    """
    Execute a DAG run. When run_dag_node_task is provided (by Celery), use canvas for parallel waves;
    otherwise run nodes sequentially. Updates dag_runs and dag_run_nodes. Returns summary dict.
    """
    from storage.db import (
        get_dag_run,
        update_dag_run,
        update_dag_run_heartbeat,
        upsert_dag_run_node,
        is_enabled,
    )

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
    update_dag_run_heartbeat(run_id)
    order = _topological_order(nodes, edges)
    if len(order) != len(nodes):
        update_dag_run(run_id, status="failed", error_message="Graph has cycle")
        return {"success": False, "error": "Cycle detected"}

    # Use Celery canvas when task is provided (parallel waves)
    if run_dag_node_task is not None:
        from src.backend.dag_compiler import build_dag_canvas
        canvas = build_dag_canvas(run_id, nodes, edges, run_dag_node_task)
        if canvas is None:
            update_dag_run(run_id, status="failed", error_message="Graph has cycle")
            return {"success": False, "error": "Cycle detected"}
        stop_heartbeat = threading.Event()
        heartbeat_thread = threading.Thread(target=_heartbeat_loop, args=(run_id, stop_heartbeat), daemon=True)
        heartbeat_thread.start()
        try:
            result = canvas.apply_async()
            result.get(timeout=3600)
            update_dag_run(run_id, status="success", finished_at=datetime.now(timezone.utc))
            return {"success": True, "run_id": run_id}
        except Exception as e:
            # Node task already updated run to failed if it failed
            run_after = get_dag_run(run_id)
            if run_after and run_after.get("status") == "running":
                update_dag_run(run_id, status="failed", finished_at=datetime.now(timezone.utc), error_message=str(e))
            return {"success": False, "error": str(e), "run_id": run_id}
        finally:
            stop_heartbeat.set()
            heartbeat_thread.join(timeout=2)

    # Sequential fallback (no Celery canvas)
    work_dir = Path(tempfile.mkdtemp(prefix="qasic_dag_"))
    node_outputs: dict[str, dict] = {}
    now = datetime.now(timezone.utc)
    stop_heartbeat = threading.Event()
    heartbeat_thread = threading.Thread(target=_heartbeat_loop, args=(run_id, stop_heartbeat), daemon=True)
    heartbeat_thread.start()

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

            inputs = _get_inputs_for_node(node_id, nodes, edges, node_outputs)

            upsert_dag_run_node(run_id, node_id, status="running", started_at=now)

            outputs, err = dispatcher_dispatch(task_type, config, inputs, work_dir)

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

        update_dag_run(run_id, status="success", finished_at=datetime.now(timezone.utc))
        return {"success": True, "run_id": run_id}
    finally:
        stop_heartbeat.set()
        heartbeat_thread.join(timeout=2)
        try:
            import shutil
            shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            pass
