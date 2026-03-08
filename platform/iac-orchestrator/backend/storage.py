"""In-memory storage for pipelines and runs. Can be replaced with SQLite/DB later."""
from __future__ import annotations

from typing import Any

_pipelines: dict[int, dict] = {}
_runs: dict[int, dict] = {}
_next_pipeline_id = 1
_next_run_id = 1


def list_pipelines() -> list[dict]:
    return list(_pipelines.values())


def get_pipeline(pid: int) -> dict | None:
    return _pipelines.get(pid)


def create_pipeline(name: str, nodes: list[dict], edges: list[dict]) -> dict:
    global _next_pipeline_id
    pid = _next_pipeline_id
    _next_pipeline_id += 1
    rec = {"id": pid, "name": name, "nodes": nodes, "edges": edges}
    _pipelines[pid] = rec
    return rec


def update_pipeline(pid: int, name: str | None = None, nodes: list[dict] | None = None, edges: list[dict] | None = None) -> dict | None:
    rec = _pipelines.get(pid)
    if not rec:
        return None
    if name is not None:
        rec["name"] = name
    if nodes is not None:
        rec["nodes"] = nodes
    if edges is not None:
        rec["edges"] = edges
    return rec


def delete_pipeline(pid: int) -> bool:
    if pid not in _pipelines:
        return False
    del _pipelines[pid]
    return True


def list_runs(pipeline_id: int) -> list[dict]:
    return [r for r in _runs.values() if r.get("pipeline_id") == pipeline_id]


def get_run(run_id: int) -> dict | None:
    return _runs.get(run_id)


def create_run(pipeline_id: int) -> dict:
    global _next_run_id
    rid = _next_run_id
    _next_run_id += 1
    rec = {
        "id": rid,
        "pipeline_id": pipeline_id,
        "status": "pending",
        "stages": {},
        "message": "",
    }
    _runs[rid] = rec
    return rec


def update_run(run_id: int, status: str | None = None, stages: dict | None = None, message: str | None = None) -> dict | None:
    rec = _runs.get(run_id)
    if not rec:
        return None
    if status is not None:
        rec["status"] = status
    if stages is not None:
        rec["stages"] = stages
    if message is not None:
        rec["message"] = message
    return rec


def update_run_stage(run_id: int, node_id: str, stage_data: dict[str, Any]) -> dict | None:
    rec = _runs.get(run_id)
    if not rec:
        return None
    s = rec.setdefault("stages", {})
    s[node_id] = {**s.get(node_id, {}), **stage_data}
    return rec
