"""
IaC Orchestrator API: pipeline CRUD, run pipeline, run status/logs, approval.
Run with: uvicorn backend.main:app --reload (from tools/iac-orchestrator)
"""
from __future__ import annotations

import os
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import storage
from .executor import run_pipeline, run_stage
from .models import (
    ApprovalPayload,
    PipelineCreate,
    PipelineEdge,
    PipelineNode,
    PipelineResponse,
    PipelineUpdate,
    RunResponse,
    RunStageStatus,
)

# Repo root: parent of qasic-engineering-as-code when running in repo; else cwd
REPO_ROOT = Path(os.environ.get("IAC_ORCHESTRATOR_REPO_ROOT", Path.cwd()))
if REPO_ROOT.name == "iac-orchestrator":
    REPO_ROOT = REPO_ROOT.parent.parent  # tools/iac-orchestrator -> repo root
elif REPO_ROOT.name == "tools":
    REPO_ROOT = REPO_ROOT.parent

app = FastAPI(title="IaC Orchestrator", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _run_pipeline_async(run_id: int) -> None:
    run_pipeline(run_id, REPO_ROOT)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/stage-types")
def list_stage_types():
    """Return stage types for the palette."""
    return {
        "stage_types": [
            {"id": "tofu_init", "label": "Tofu init"},
            {"id": "tofu_plan", "label": "Tofu plan"},
            {"id": "tofu_apply", "label": "Tofu apply"},
            {"id": "tofu_destroy", "label": "Tofu destroy"},
            {"id": "approval", "label": "Approval"},
            {"id": "script", "label": "Script"},
        ]
    }


@app.get("/api/pipelines", response_model=dict)
def list_pipelines():
    return {"pipelines": storage.list_pipelines()}


@app.get("/api/pipelines/{pipeline_id}", response_model=PipelineResponse)
def get_pipeline(pipeline_id: int):
    p = storage.get_pipeline(pipeline_id)
    if not p:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return PipelineResponse(**p)


@app.post("/api/pipelines", response_model=PipelineResponse)
def create_pipeline(body: PipelineCreate):
    nodes = [n.model_dump() for n in body.nodes]
    edges = [e.model_dump() for e in body.edges]
    rec = storage.create_pipeline(body.name, nodes, edges)
    return PipelineResponse(**rec)


@app.put("/api/pipelines/{pipeline_id}", response_model=PipelineResponse)
def update_pipeline(pipeline_id: int, body: PipelineUpdate):
    p = storage.get_pipeline(pipeline_id)
    if not p:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    nodes = [PipelineNode(**n).model_dump() for n in (body.nodes or p["nodes"])]
    edges = [PipelineEdge(**e).model_dump() for e in (body.edges or p["edges"])]
    rec = storage.update_pipeline(pipeline_id, name=body.name or p["name"], nodes=nodes, edges=edges)
    return PipelineResponse(**rec)


@app.post("/api/pipelines/{pipeline_id}/run")
def start_run(pipeline_id: int):
    p = storage.get_pipeline(pipeline_id)
    if not p:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    rec = storage.create_run(pipeline_id)
    run_id = rec["id"]
    thread = threading.Thread(target=_run_pipeline_async, args=(run_id,))
    thread.daemon = True
    thread.start()
    return {"run_id": run_id, "message": "Run started"}


@app.get("/api/runs/{run_id}", response_model=RunResponse)
def get_run(run_id: int):
    rec = storage.get_run(run_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Run not found")
    stages_list = [
        RunStageStatus(
            node_id=nid,
            status=s.get("status", "pending"),
            stdout=s.get("stdout", ""),
            stderr=s.get("stderr", ""),
            exit_code=s.get("exit_code"),
            output=s.get("output", {}),
        )
        for nid, s in (rec.get("stages") or {}).items()
    ]
    return RunResponse(
        id=rec["id"],
        pipeline_id=rec["pipeline_id"],
        status=rec["status"],
        stages=stages_list,
        message=rec.get("message", ""),
    )


@app.get("/api/pipelines/{pipeline_id}/runs")
def list_runs(pipeline_id: int):
    return {"runs": storage.list_runs(pipeline_id)}


@app.post("/api/runs/{run_id}/approve/{node_id}")
def approve_stage(run_id: int, node_id: str, body: ApprovalPayload):
    rec = storage.get_run(run_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Run not found")
    stages = rec.get("stages") or {}
    stage_data = stages.get(node_id) or {}
    if stage_data.get("status") != "waiting_approval":
        raise HTTPException(status_code=400, detail="Stage is not waiting for approval")
    storage.update_run_stage(run_id, node_id, {"status": "success" if body.approved else "failed"})
    if body.approved:
        thread = threading.Thread(target=_run_pipeline_async, args=(run_id,))
        thread.daemon = True
        thread.start()
    else:
        storage.update_run(run_id, status="failed", message=f"Approval rejected: {node_id}")
    return {"ok": True}
