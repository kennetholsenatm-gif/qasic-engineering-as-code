"""Pydantic models for pipelines, runs, and stage config."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

StageType = Literal["tofu_init", "tofu_plan", "tofu_apply", "tofu_destroy", "approval", "script"]


class StageConfig(BaseModel):
    """Per-stage configuration (Tofu path, workspace, vars, script, etc.)."""
    # OpenTofu stages
    tofu_root: str | None = Field(None, description="Path to Tofu root (e.g. infra/tofu)")
    workspace: str | None = Field(None, description="OpenTofu workspace name")
    var_file: str | None = Field(None, description="Optional -var-file path")
    vars: dict[str, Any] = Field(default_factory=dict, description="Key-value vars for Tofu")
    # Script stage
    script_path: str | None = Field(None, description="Path to script or command to run")
    script_args: list[str] = Field(default_factory=list, description="Arguments for script/command")
    # Approval: no extra config; executor waits for API approval


class PipelineNode(BaseModel):
    """A single node in the pipeline graph."""
    id: str
    type: str = "stageNode"
    data: dict[str, Any] = Field(default_factory=dict)  # label, stage_type, config
    position: dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0})


class PipelineEdge(BaseModel):
    """An edge between two nodes."""
    id: str
    source: str
    target: str
    sourceHandle: str | None = None
    targetHandle: str | None = None


class PipelineCreate(BaseModel):
    """Payload to create a pipeline."""
    name: str
    nodes: list[PipelineNode]
    edges: list[PipelineEdge]


class PipelineUpdate(BaseModel):
    """Payload to update a pipeline."""
    name: str | None = None
    nodes: list[PipelineNode] | None = None
    edges: list[PipelineEdge] | None = None


class PipelineResponse(BaseModel):
    """Pipeline as returned by API."""
    id: int
    name: str
    nodes: list[dict]
    edges: list[dict]


class RunStageStatus(BaseModel):
    """Status of one stage in a run."""
    node_id: str
    status: Literal["pending", "running", "success", "failed", "waiting_approval"]
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    output: dict[str, Any] = Field(default_factory=dict)


class RunResponse(BaseModel):
    """A single run as returned by API."""
    id: int
    pipeline_id: int
    status: Literal["pending", "running", "success", "failed"]
    stages: list[RunStageStatus] = Field(default_factory=list)
    message: str = ""


class ApprovalPayload(BaseModel):
    """Payload to approve or reject an approval stage."""
    approved: bool
