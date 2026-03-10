"""
FastAPI backend for QASIC Engineering-as-Code.
Provides API routes to run protocol, routing, pipeline, inverse design,
quantum illumination, quantum radar; return latest results and doc links.
Run with: uvicorn src.backend.main:app --reload (from repo root, PYTHONPATH=.).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Literal

import asyncio
from fastapi import Body, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

# IBM protocol jobs: Redis-backed when CELERY_BROKER_URL set (multi-worker); else in-memory (single-worker)
# Use src.backend.job_store.get_job / set_job

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from config.logger import get_logger
    log = get_logger(__name__)
except ImportError:
    log = None  # optional structured logging

# Load app config from config/app_config.yaml (env overrides: BACKEND_CORS_ORIGINS, QASIC_PIPELINE_BASE)
def _get_app_cfg():
    from config import get_app_config
    return get_app_config()

_app_cfg = _get_app_cfg()
ENGINEERING_DIR = REPO_ROOT / _app_cfg.paths.engineering_dir
DOCS_DIR = REPO_ROOT / _app_cfg.paths.docs_dir
PIPELINE_BASE = _app_cfg.paths.pipeline_base
ROUTING_JSON = ENGINEERING_DIR / f"{PIPELINE_BASE}_routing.json"
INVERSE_JSON = ENGINEERING_DIR / f"{PIPELINE_BASE}_inverse.json"

# CORS: strict whitelist in production. allow_credentials=True with allow_origins=["*"] is insecure (CSRF/data exfiltration).
_cors_origins = (_app_cfg.cors.allow_origins or "").strip()
if _cors_origins == "*" or not _cors_origins:
    _allow_origins = ["*"]  # dev default; set BACKEND_CORS_ORIGINS for production
else:
    _allow_origins = [o.strip() for o in _cors_origins.split(",") if o.strip()]
_allow_credentials = _app_cfg.cors.allow_credentials and "*" not in _allow_origins

app = FastAPI(title=_app_cfg.title, version=_app_cfg.version)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins if _allow_origins else ["*"],
    allow_credentials=_allow_credentials,
    allow_methods=_app_cfg.cors.allow_methods,
    allow_headers=_app_cfg.cors.allow_headers,
)

# Rate limiting (slowapi): protect heavy compute; key by IP or X-Forwarded-For
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    limiter = Limiter(key_func=get_remote_address, default_limits=["200/hour"])
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    limit_heavy = limiter.limit("15/minute")  # pipeline, inverse, routing, protocol
except ImportError:
    limiter = None
    limit_heavy = lambda f: f  # no-op


# --- Feature Flags & Dynamic Modules (Infrastructure-aware) ---
def _is_feature_enabled(feature_name: str) -> bool:
    """Check if a feature flag is enabled via environment variables (FEATURE_<NAME>_ENABLED)."""
    key = f"FEATURE_{feature_name.upper()}_ENABLED"
    val = os.environ.get(key, "false").strip().lower()
    return val in ("1", "true", "yes", "on")


def _load_feature_modules() -> None:
    """Conditionally mount API routers from src.backend.modules based on FEATURE_*_ENABLED."""
    features = [
        ("keycloak", "auth_keycloak", "keycloak_router", "/api/auth/keycloak", "Keycloak"),
        ("elasticache", "advanced_cache", "cache_router", "/api/cache", "Advanced Cache"),
    ]
    for name, module_name, router_attr, prefix, tag in features:
        if not _is_feature_enabled(name):
            continue
        try:
            mod = __import__(f"src.backend.modules.{module_name}", fromlist=[router_attr])
            router = getattr(mod, router_attr)
            app.include_router(router, prefix=prefix, tags=[tag])
            if log:
                log.info("Feature module enabled: %s (prefix=%s)", name, prefix)
        except ImportError as e:
            if log:
                log.warning("Failed to load feature module %s: %s", name, e)


_load_feature_modules()


def _run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    """Run command; return (exit_code, stderr_or_stdout)."""
    r = subprocess.run(
        cmd,
        cwd=cwd or REPO_ROOT,
        capture_output=True,
        text=True,
    )
    err = (r.stderr or "").strip() or (r.stdout or "").strip()
    return r.returncode, err


def _sanitize_detail(exc: Exception, default: str) -> str:
    """Return safe detail for HTTPException; log full exception. Avoid exposing paths/stack to client (AppSec)."""
    if log:
        log.exception("Request error: %s", exc)
    if os.environ.get("QASIC_DEBUG", "").strip().lower() in ("1", "true", "yes"):
        return str(exc)
    return default


# --- Request bodies (strict Literal to prevent argument injection into subprocess) ---
BackendKind = Literal["sim", "hardware"]
ProtocolKind = Literal["teleport", "bb84", "e91"]
TopologyKind = Literal["linear", "linear_chain", "star", "repeater", "repeater_chain"]
RoutingMethodKind = Literal["qaoa", "rl"]
ModelKind = Literal["mlp", "gnn"]
DeviceKind = Literal["auto", "cpu", "cuda", "mps"]


class RunProtocolRequest(BaseModel):
    protocol: ProtocolKind = "teleport"
    backend: BackendKind = "sim"
    use_circuit_function: bool = False


class RunRoutingRequest(BaseModel):
    backend: BackendKind = "sim"
    fast: bool = False
    topology: TopologyKind | None = None
    qubits: int | None = None
    hub: int | None = None
    routing_method: RoutingMethodKind | None = None


# Max QASM length to avoid abuse (e.g. 100KB)
QASM_STRING_MAX_LENGTH = 100_000


class RunPipelineRequest(BaseModel):
    backend: BackendKind = "sim"
    fast: bool = False
    routing_method: RoutingMethodKind | None = None
    model: ModelKind | None = None
    heac: bool = False
    skip_routing: bool = False
    skip_inverse: bool = False
    project_id: int | None = None
    # Phase 1: circuit ingestion — when set, run qasm_to_asic and return that result (sync or async)
    qasm_string: str | None = None
    circuit_name: str | None = None
    # Phase 2: when True and qasm_string is set, run full pipeline with circuit-derived routing
    full_pipeline_with_circuit: bool = False
    # Transpile unsupported gates (T, S, Rz, U3, etc.) to ASIC basis (H, X, Z, Rx, CNOT)
    decompose_to_asic: bool = False


class ValidateQasmRequest(BaseModel):
    qasm_string: str = ""
    decompose_to_asic: bool = False


class RunInverseRequest(BaseModel):
    phase_band: str | None = None
    routing_result_path: str | None = None
    model: ModelKind | None = None
    device: DeviceKind | None = None


class QuantumIlluminationRequest(BaseModel):
    eta: float = 0.1


class QuantumRadarRequest(BaseModel):
    eta: float = 0.1
    n_b: float = 10.0
    r: float = 0.5


class QuantumRadarSweepRequest(BaseModel):
    param: str = "r"  # eta | n_b | r
    min_val: float | None = None
    max_val: float | None = None
    steps: int = 21
    eta: float = 0.2
    n_b: float = 2.0
    r: float = 0.5


class QuantumRadarOptimizeRequest(BaseModel):
    param: str = "r"
    optimize_min: float | None = None
    optimize_max: float | None = None
    steps: int = 50
    eta: float = 0.2
    n_b: float = 2.0
    r: float = 0.5
    maximize: str = "mutual_info"  # mutual_info | snr


class RunQKDRequest(BaseModel):
    protocol: Literal["bb84", "e91"] = "bb84"
    n_bits: int = 64
    n_trials: int = 500  # for E91
    seed: int | None = None


class QRNCMintRequest(BaseModel):
    num_bytes: int = 32
    use_real_hardware: bool = False
    ibm_token: str | None = None
    token_id: str | None = None


class QRNCExchangeRequest(BaseModel):
    token_a_hex: str
    token_b_hex: str
    party_a_id: str = "Alice"
    party_b_id: str = "Bob"


class BQTCRunCycleRequest(BaseModel):
    dry_run: bool = True  # BQTC pipeline.yaml actuator.dry_run is separate; this is for API docs


class CreateProjectRequest(BaseModel):
    name: str
    description: str | None = None
    config: dict | None = None


class UpdateProjectRequest(BaseModel):
    name: str | None = None
    description: str | None = None


@app.get("/api/projects")
def list_projects_api():
    """List all projects (project-based workspace)."""
    try:
        from storage.db import list_projects, is_enabled
        if not is_enabled():
            return {"projects": []}
        return {"projects": list_projects()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_sanitize_detail(e, "Failed to list projects."))


@app.post("/api/projects")
def create_project_api(req: CreateProjectRequest):
    """Create a project. Returns project id and mlflow_experiment_id when MLflow is configured."""
    try:
        from storage.db import create_project, get_project, update_project_mlflow_experiment, is_enabled
        if not is_enabled():
            raise HTTPException(status_code=503, detail="Database not configured (set DATABASE_URL).")
        pid = create_project(req.name, req.description, req.config)
        if pid is None:
            raise HTTPException(status_code=400, detail="Project name may already exist.")
        proj = get_project(pid)
        if proj and os.environ.get("MLFLOW_TRACKING_URI"):
            try:
                from storage.artifacts_mlflow import get_or_create_experiment
                exp_name = f"qasic-project-{req.name.replace(' ', '_')}"
                eid = get_or_create_experiment(exp_name)
                if eid:
                    update_project_mlflow_experiment(pid, eid)
                    proj["mlflow_experiment_id"] = eid
            except Exception:
                pass
        return proj or {"id": pid, "name": req.name, "description": req.description or "", "config": req.config or {}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_sanitize_detail(e, "Failed to create project."))


@app.get("/api/projects/{project_id}")
def get_project_api(project_id: int):
    """Get a single project by id."""
    try:
        from storage.db import get_project, is_enabled
        if not is_enabled():
            raise HTTPException(status_code=503, detail="Database not configured.")
        proj = get_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found.")
        return proj
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_sanitize_detail(e, "Failed to get project."))


@app.put("/api/projects/{project_id}")
def update_project_api(project_id: int, req: UpdateProjectRequest):
    """Update a project's name and/or description."""
    try:
        from storage.db import get_project, update_project, is_enabled
        if not is_enabled():
            raise HTTPException(status_code=503, detail="Database not configured.")
        proj = get_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found.")
        ok = update_project(project_id, name=req.name, description=req.description)
        if not ok:
            raise HTTPException(status_code=500, detail="Failed to update project.")
        return get_project(project_id) or proj
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_sanitize_detail(e, "Failed to update project."))


@app.delete("/api/projects/{project_id}")
def delete_project_api(project_id: int):
    """Delete a project."""
    try:
        from storage.db import get_project, delete_project, is_enabled
        if not is_enabled():
            raise HTTPException(status_code=503, detail="Database not configured.")
        if not get_project(project_id):
            raise HTTPException(status_code=404, detail="Project not found.")
        ok = delete_project(project_id)
        if not ok:
            raise HTTPException(status_code=500, detail="Failed to delete project.")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_sanitize_detail(e, "Failed to delete project."))


@app.get("/api/projects/{project_id}/runs")
def list_project_runs_api(project_id: int, limit: int = 50):
    """List pipeline runs for a project."""
    try:
        from storage.db import list_pipeline_runs, get_project, is_enabled
        if not is_enabled():
            return {"runs": []}
        proj = get_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found.")
        return {"runs": list_pipeline_runs(project_id=project_id, limit=limit)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_sanitize_detail(e, "Failed to list runs."))


@app.get("/api/projects/{project_id}/runs/{run_id}/artifacts")
def list_run_artifacts_api(project_id: int, run_id: int):
    """List artifact descriptors for a pipeline run (download URLs and types)."""
    try:
        from storage.db import get_pipeline_run, get_project, is_enabled
        if not is_enabled():
            return {"artifacts": []}
        proj = get_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found.")
        run = get_pipeline_run(run_id)
        if not run or run.get("project_id") != project_id:
            raise HTTPException(status_code=404, detail="Run not found.")
        artifacts = []
        if run.get("routing_path") and os.path.isfile(run["routing_path"]):
            artifacts.append({"name": "routing_result.json", "type": "application/json", "url": f"/api/runs/{run_id}/artifacts/routing_result.json"})
        if run.get("inverse_path") and os.path.isfile(run["inverse_path"]):
            artifacts.append({"name": "inverse_result.json", "type": "application/json", "url": f"/api/runs/{run_id}/artifacts/inverse_result.json"})
        if run.get("gds_path") and os.path.isfile(run["gds_path"]):
            artifacts.append({"name": "output.gds", "type": "application/octet-stream", "url": f"/api/runs/{run_id}/artifacts/gds"})
        return {"artifacts": artifacts}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_sanitize_detail(e, "Failed to list artifacts."))


@app.get("/api/runs/{run_id}/artifacts/{artifact_name:path}")
def download_run_artifact_api(run_id: int, artifact_name: str):
    """Download an artifact file for a pipeline run (routing_result.json, inverse_result.json, gds)."""
    try:
        from storage.db import get_pipeline_run, is_enabled
        if not is_enabled():
            raise HTTPException(status_code=503, detail="Database not configured.")
        run = get_pipeline_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found.")
        name = artifact_name.strip().lower().rstrip("/")
        path = None
        filename = None
        if name in ("routing_result.json", "routing"):
            path = run.get("routing_path")
            filename = "routing_result.json"
        elif name in ("inverse_result.json", "inverse"):
            path = run.get("inverse_path")
            filename = "inverse_result.json"
        elif name in ("gds", "output.gds"):
            path = run.get("gds_path")
            filename = "output.gds"
        if not path or not os.path.isfile(path):
            raise HTTPException(status_code=404, detail="Artifact not found.")
        return FileResponse(path, filename=filename or os.path.basename(path))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_sanitize_detail(e, "Failed to download artifact."))


@app.get("/api/runs/compare")
def compare_runs_api(run_id_a: int, run_id_b: int):
    """Return config and key metrics for two pipeline runs (for side-by-side comparison)."""
    try:
        from storage.db import get_pipeline_run, is_enabled
        if not is_enabled():
            raise HTTPException(status_code=503, detail="Database not configured.")
        run_a = get_pipeline_run(run_id_a)
        run_b = get_pipeline_run(run_id_b)
        if not run_a:
            raise HTTPException(status_code=404, detail=f"Run {run_id_a} not found.")
        if not run_b:
            raise HTTPException(status_code=404, detail=f"Run {run_id_b} not found.")
        def _summary(run):
            out = {"id": run["id"], "status": run.get("status"), "started_at": run.get("started_at"), "finished_at": run.get("finished_at"), "config": run.get("config")}
            routing, inverse = None, None
            if run.get("routing_path") and os.path.isfile(run["routing_path"]):
                try:
                    with open(run["routing_path"], encoding="utf-8") as f:
                        routing = json.load(f)
                except Exception:
                    pass
            if run.get("inverse_path") and os.path.isfile(run["inverse_path"]):
                try:
                    with open(run["inverse_path"], encoding="utf-8") as f:
                        inverse = json.load(f)
                except Exception:
                    pass
            if routing and isinstance(routing, dict):
                out["routing_cost"] = routing.get("cost") or routing.get("energy")
                out["topology"] = routing.get("topology") or routing.get("topology_name")
            if inverse and isinstance(inverse, dict):
                out["phase_min"] = inverse.get("phase_min")
                out["phase_max"] = inverse.get("phase_max")
                out["phase_mean"] = inverse.get("phase_mean")
                out["num_meta_atoms"] = inverse.get("num_meta_atoms")
            return out
        return {"run_a": _summary(run_a), "run_b": _summary(run_b)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_sanitize_detail(e, "Failed to compare runs."))


# --- DAG orchestrator (task types, CRUD, validate) ---

class DAGCreateRequest(BaseModel):
    name: str
    project_id: int | None = None
    nodes: list = []
    edges: list = []


class DAGUpdateRequest(BaseModel):
    name: str | None = None
    nodes: list | None = None
    edges: list | None = None


class DAGValidateRequest(BaseModel):
    nodes: list = []
    edges: list = []


class RunDagRequest(BaseModel):
    qasm_string: str | None = None
    circuit_name: str | None = None
    run_mode: Literal["dag", "circuit_pipeline"] = "dag"
    decompose_to_asic: bool = False
    project_id: int | None = None


# --- Settings: credentials vault (no raw secrets in response) ---

class CredentialsSaveRequest(BaseModel):
    ibm_quantum_token: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None


class CredentialsSourceRequest(BaseModel):
    credentials_source: Literal["vault", "file"] = "vault"
    credentials_path: str | None = None


@app.get("/api/settings/credentials")
def get_credentials_api():
    """Return credentials status only (which keys configured, source, path). Never returns secret values."""
    try:
        from src.backend.credentials_vault import get_credentials_status
        cfg = _get_app_cfg()
        path = getattr(cfg.paths, "credentials_file", None) or ""
        return get_credentials_status(path, REPO_ROOT)
    except Exception as e:
        raise HTTPException(status_code=500, detail=_sanitize_detail(e, "Failed to read credentials status."))


@app.post("/api/settings/credentials")
def save_credentials_api(req: CredentialsSaveRequest):
    """Save provided credentials to vault. Validate payload size; only allowed keys stored."""
    try:
        from src.backend.credentials_vault import write_vault
        cfg = _get_app_cfg()
        path = getattr(cfg.paths, "credentials_file", None) or ""
        payload = {k: v for k, v in req.model_dump().items() if v is not None and v != ""}
        if len(json.dumps(payload)) > 16 * 1024:
            raise HTTPException(status_code=400, detail="Credentials payload too large.")
        write_vault(path, REPO_ROOT, payload)
        return {"message": "Credentials saved to vault."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=_sanitize_detail(e, "Failed to save credentials."))


@app.post("/api/settings/credentials/source")
def set_credentials_source_api(req: CredentialsSourceRequest):
    """Set credentials source to vault or external file (path required for file)."""
    try:
        from src.backend.credentials_vault import set_credentials_source
        set_credentials_source(REPO_ROOT, req.credentials_source, req.credentials_path or "")
        return {"message": "Credentials source updated."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=_sanitize_detail(e, "Failed to set credentials source."))


@app.get("/api/dag/task-types")
def get_dag_task_types():
    """Return task type registry for palette and validation (inputs, outputs, backends)."""
    try:
        from src.backend.task_registry import list_task_types
        return {"task_types": list_task_types()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_sanitize_detail(e, "Failed to load task types."))


@app.get("/api/dag")
def list_dags_api(project_id: int | None = None, limit: int = 100):
    """List DAG definitions, optionally by project_id."""
    try:
        from storage.db import list_dags, is_enabled
        if not is_enabled():
            return {"dags": []}
        return {"dags": list_dags(project_id=project_id, limit=limit)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_sanitize_detail(e, "Failed to list DAGs."))


@app.post("/api/dag")
def create_dag_api(req: DAGCreateRequest):
    """Create a DAG definition."""
    try:
        from storage.db import create_dag, get_dag, is_enabled
        if not is_enabled():
            raise HTTPException(status_code=503, detail="Database not configured (set DATABASE_URL).")
        dag_id = create_dag(req.name, req.nodes, req.edges, req.project_id)
        if dag_id is None:
            raise HTTPException(status_code=500, detail="Failed to create DAG.")
        d = get_dag(dag_id)
        return d or {"id": dag_id, "name": req.name, "project_id": req.project_id, "nodes": req.nodes, "edges": req.edges}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_sanitize_detail(e, "Failed to create DAG."))


@app.get("/api/dag/{dag_id}")
def get_dag_api(dag_id: int):
    """Get a DAG definition by id."""
    try:
        from storage.db import get_dag, is_enabled
        if not is_enabled():
            raise HTTPException(status_code=503, detail="Database not configured.")
        d = get_dag(dag_id)
        if not d:
            raise HTTPException(status_code=404, detail="DAG not found.")
        return d
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_sanitize_detail(e, "Failed to get DAG."))


@app.put("/api/dag/{dag_id}")
def update_dag_api(dag_id: int, req: DAGUpdateRequest):
    """Update a DAG definition."""
    try:
        from storage.db import update_dag, get_dag, is_enabled
        if not is_enabled():
            raise HTTPException(status_code=503, detail="Database not configured.")
        updated = update_dag(dag_id, name=req.name, nodes=req.nodes, edges=req.edges)
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to update DAG.")
        d = get_dag(dag_id)
        return d or {"id": dag_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_sanitize_detail(e, "Failed to update DAG."))


@app.post("/api/dag/validate")
def validate_dag_api(req: DAGValidateRequest):
    """Validate a DAG (acyclic, task types, backends, required inputs). Returns list of errors."""
    try:
        from src.backend.dag_validate import validate_dag
        errors = validate_dag(req.nodes, req.edges)
        return {"valid": len(errors) == 0, "errors": errors}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_sanitize_detail(e, "Validation failed."))


@app.post("/api/dag/{dag_id}/run")
@limit_heavy
def run_dag_api(request: Request, dag_id: int, body: RunDagRequest | None = Body(None)):
    """Create a DAG run and enqueue execution (Celery). Optional body: run_mode=circuit_pipeline + qasm_string runs full pipeline from circuit. Returns run_id and task_id when Celery available."""
    try:
        from storage.db import get_dag, create_dag_run, update_dag_run, is_enabled
        if not is_enabled():
            raise HTTPException(status_code=503, detail="Database not configured (set DATABASE_URL).")
        d = get_dag(dag_id)
        if not d:
            raise HTTPException(status_code=404, detail="DAG not found.")
        req = body or RunDagRequest()
        run_mode = req.run_mode or "dag"
        qasm_string = (req.qasm_string or "").strip()
        circuit_name = (req.circuit_name or "circuit").strip() or "circuit"

        if run_mode == "circuit_pipeline" and qasm_string:
            _validate_qasm_string(qasm_string, decompose_to_asic=req.decompose_to_asic)
            if not _celery_available():
                raise HTTPException(status_code=503, detail="Celery/Redis required for circuit-driven pipeline (set CELERY_BROKER_URL).")
            run_id = create_dag_run(dag_id=dag_id, status="pending", nodes_snapshot=[], edges_snapshot=[])
            if run_id is None:
                raise HTTPException(status_code=500, detail="Failed to create run.")
            from src.backend.tasks import run_pipeline_with_circuit_task
            task = run_pipeline_with_circuit_task.delay(
                qasm_string=qasm_string,
                circuit_name=circuit_name,
                output_base=PIPELINE_BASE,
                fast=False,
                routing_method="qaoa",
                model="mlp",
                heac=False,
                hardware=False,
                run_id=run_id,
                decompose_to_asic=req.decompose_to_asic,
            )
            update_dag_run(run_id, celery_task_id=task.id)
            return {"run_id": run_id, "task_id": task.id, "status": "pending", "message": "Circuit-driven pipeline enqueued."}

        nodes = d.get("nodes") or []
        edges = d.get("edges") or []
        run_id = create_dag_run(dag_id=dag_id, status="pending", nodes_snapshot=nodes, edges_snapshot=edges)
        if run_id is None:
            raise HTTPException(status_code=500, detail="Failed to create run.")
        task_id = None
        if _celery_available():
            from src.backend.tasks import run_dag_task
            task = run_dag_task.delay(run_id)
            task_id = task.id
            update_dag_run(run_id, celery_task_id=task_id)
            return {"run_id": run_id, "task_id": task_id, "status": "pending", "message": "Run enqueued; execution in progress."}
        return {"run_id": run_id, "status": "pending", "message": "Run created; start Celery worker to execute."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_sanitize_detail(e, "Failed to start run."))


@app.get("/api/dag/runs/{run_id}")
def get_dag_run_api(run_id: int):
    """Get DAG run status and node-level status."""
    try:
        from storage.db import get_dag_run, is_enabled
        if not is_enabled():
            raise HTTPException(status_code=503, detail="Database not configured.")
        r = get_dag_run(run_id)
        if not r:
            raise HTTPException(status_code=404, detail="Run not found.")
        return r
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_sanitize_detail(e, "Failed to get run."))


@app.get("/api/dag/{dag_id}/runs")
def list_dag_runs_api(dag_id: int, limit: int = 50):
    """List runs for a DAG."""
    try:
        from storage.db import list_dag_runs, get_dag, is_enabled
        if not is_enabled():
            return {"runs": []}
        d = get_dag(dag_id)
        if not d:
            raise HTTPException(status_code=404, detail="DAG not found.")
        return {"runs": list_dag_runs(dag_id=dag_id, limit=limit)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_sanitize_detail(e, "Failed to list runs."))


@app.post("/api/validate_qasm")
def validate_qasm_api(body: ValidateQasmRequest = Body(...)):
    """Validate QASM string for parse and gate support. Returns valid flag and optional error/line for editor."""
    qasm_string = (body.qasm_string or "").strip()
    if not qasm_string:
        return {"valid": True}
    if len(qasm_string) > QASM_STRING_MAX_LENGTH:
        return {
            "valid": False,
            "error": f"QASM string too long (max {QASM_STRING_MAX_LENGTH} characters)",
            "line": None,
        }
    try:
        from src.core_compute.asic.qasm_loader import interaction_graph_from_qasm_string
        G = interaction_graph_from_qasm_string(qasm_string, decompose_to_asic=body.decompose_to_asic)
        return {"valid": True, "qubit_count": G.number_of_nodes(), "edge_count": G.number_of_edges()}
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="QASM validation is performed by the compute worker. Use async pipeline or ensure the worker is running (control-plane-only mode).",
        )
    except Exception as e:
        line = getattr(e, "line", None)
        try:
            from src.core_compute.asic.qasm_loader import QasmParseError
            actionable = isinstance(e, QasmParseError) or "qiskit-qasm3-import" in str(e)
        except ImportError:
            actionable = "qiskit-qasm3-import" in str(e)
        debug = os.environ.get("QASIC_DEBUG", "").strip().lower() in ("1", "true", "yes")
        msg = str(e) if (actionable or debug) else "Invalid QASM: parse or gate error"
        if log:
            log.exception("QASM validation failed: %s", e)
        return {"valid": False, "error": msg, "line": line}


@app.post("/api/circuit/topology")
def circuit_topology_api(body: ValidateQasmRequest = Body(...)):
    """Build qubit interaction graph from QASM for Circuit Topology DAG (EaC view). Returns nodes/edges for React Flow."""
    qasm_string = (body.qasm_string or "").strip()
    if not qasm_string:
        raise HTTPException(status_code=400, detail="qasm_string is required")
    if len(qasm_string) > QASM_STRING_MAX_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"QASM string too long (max {QASM_STRING_MAX_LENGTH} characters)",
        )
    try:
        from src.core_compute.asic.qasm_loader import interaction_graph_from_qasm_string
        G = interaction_graph_from_qasm_string(qasm_string, decompose_to_asic=body.decompose_to_asic)
    except Exception as e:
        line = getattr(e, "line", None)
        msg = _sanitize_detail(e, "Invalid QASM: parse or gate error")
        raise HTTPException(status_code=400, detail=msg)
    nodes = [{"id": f"q{i}", "label": f"q{i}"} for i in sorted(G.nodes())]
    edges = []
    for i, (u, v) in enumerate(G.edges()):
        edges.append({"id": f"e{u}-{v}", "source": f"q{u}", "target": f"q{v}"})
    return {
        "nodes": nodes,
        "edges": edges,
        "qubit_count": G.number_of_nodes(),
        "edge_count": G.number_of_edges(),
    }


@app.get("/api/pipeline/dag")
def get_pipeline_dag():
    """Return pipeline DAG (nodes and edges) for visualization (e.g. React Flow)."""
    nodes = [
        {"id": "routing", "label": "Routing", "type": "default"},
        {"id": "superscreen", "label": "SuperScreen", "type": "default"},
        {"id": "inverse_design", "label": "Inverse design", "type": "default"},
        {"id": "heac_library", "label": "HEaC library", "type": "default"},
        {"id": "heac_phases_to_geometry", "label": "Phases → Geometry", "type": "default"},
        {"id": "manifest_to_gds", "label": "Manifest → GDS", "type": "default"},
        {"id": "drc", "label": "DRC", "type": "default"},
        {"id": "lvs", "label": "LVS", "type": "default"},
        {"id": "dft", "label": "DFT", "type": "default"},
        {"id": "thermal", "label": "Thermal", "type": "default"},
        {"id": "meep_verify", "label": "MEEP verify", "type": "default"},
        {"id": "packaging", "label": "Packaging", "type": "default"},
        {"id": "parasitic", "label": "Parasitic", "type": "default"},
    ]
    edges = [
        {"id": "e1", "source": "routing", "target": "superscreen"},
        {"id": "e2", "source": "routing", "target": "inverse_design"},
        {"id": "e3", "source": "inverse_design", "target": "heac_phases_to_geometry"},
        {"id": "e4", "source": "heac_library", "target": "heac_phases_to_geometry"},
        {"id": "e5", "source": "heac_phases_to_geometry", "target": "manifest_to_gds"},
        {"id": "e6", "source": "manifest_to_gds", "target": "drc"},
        {"id": "e7", "source": "manifest_to_gds", "target": "lvs"},
        {"id": "e8", "source": "manifest_to_gds", "target": "dft"},
        {"id": "e9", "source": "routing", "target": "thermal"},
        {"id": "e10", "source": "heac_phases_to_geometry", "target": "meep_verify"},
        {"id": "e11", "source": "heac_phases_to_geometry", "target": "packaging"},
        {"id": "e12", "source": "heac_phases_to_geometry", "target": "parasitic"},
    ]
    return {"nodes": nodes, "edges": edges}


@app.get("/api/tasks/{task_id}/stream")
async def stream_task_log(task_id: str):
    """Server-Sent Events stream of task progress (Redis Pub/Sub). Use for real-time pipeline log in UI."""
    import asyncio
    redis_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
    try:
        import redis.asyncio as redis_async
    except ImportError:
        try:
            import redis
            if not hasattr(redis, "asyncio"):
                raise HTTPException(status_code=503, detail="Install redis with async support for SSE (pip install redis).")
        except ImportError:
            raise HTTPException(status_code=503, detail="Redis not installed.")
        raise HTTPException(status_code=503, detail="Use redis>=4.5 with async for SSE streaming.")
    async def event_generator():
        r = redis_async.from_url(redis_url)
        pubsub = r.pubsub()
        channel = f"qasic:task:{task_id}:log"
        await pubsub.subscribe(channel)
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=30.0)
                if message and message.get("type") == "message":
                    data = message.get("data")
                    if isinstance(data, bytes):
                        data = data.decode("utf-8", errors="replace")
                    try:
                        payload = json.loads(data) if isinstance(data, str) else data
                    except json.JSONDecodeError:
                        payload = {"message": data, "step": None, "done": False}
                    yield f"data: {json.dumps(payload)}\n\n"
                    if payload.get("done"):
                        break
                await asyncio.sleep(0.1)
        finally:
            await pubsub.unsubscribe(channel)
            await r.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/schemas/pipeline")
def get_schema_pipeline():
    """JSON Schema for pipeline config (for dynamic forms, e.g. @rjsf/core)."""
    from config.loader import PipelineConfig
    return PipelineConfig.model_json_schema()


@app.get("/api/schemas/thermal")
def get_schema_thermal():
    """JSON Schema for thermal config."""
    from config.loader import ThermalConfig
    return ThermalConfig.model_json_schema()


@app.get("/api/mlflow/runs")
def get_mlflow_runs(experiment_id: str | None = None, limit: int = 20):
    """Proxy MLflow runs for the default or given experiment (for Results dashboard metrics)."""
    try:
        from storage.artifacts_mlflow import _tracking_uri, _experiment_name, is_enabled
        from mlflow.tracking import MlflowClient
    except ImportError:
        return {"runs": []}
    if not is_enabled():
        return {"runs": []}
    uri = _tracking_uri()
    if not uri:
        return {"runs": []}
    try:
        client = MlflowClient(tracking_uri=uri)
        if experiment_id:
            exp = client.get_experiment(experiment_id)
            if not exp or exp.lifecycle_stage != "active":
                return {"runs": []}
        else:
            exp = client.get_experiment_by_name(_experiment_name())
            if not exp:
                return {"runs": []}
            experiment_id = exp.experiment_id
        runs = client.search_runs(experiment_ids=[experiment_id], max_results=limit, order_by=["start_time DESC"])
        out = []
        for r in runs:
            out.append({
                "run_id": r.info.run_id,
                "run_name": r.info.run_name,
                "start_time": r.info.start_time,
                "end_time": r.info.end_time,
                "params": dict(r.data.params) if r.data.params else {},
                "metrics": dict(r.data.metrics) if r.data.metrics else {},
            })
        return {"runs": out}
    except Exception:
        return {"runs": []}


@app.get("/api/results/gds")
def download_gds(output_base: str | None = None):
    """Download GDS file for latest run or given output_base."""
    gds_path = None
    if output_base:
        gds_path = ENGINEERING_DIR / f"{output_base}.gds"
    if not gds_path or not gds_path.is_file():
        try:
            from storage.db import get_latest_pipeline_run, is_enabled
            if is_enabled():
                row = get_latest_pipeline_run()
                if row and row.get("gds_path") and os.path.isfile(row["gds_path"]):
                    return FileResponse(row["gds_path"], filename=os.path.basename(row["gds_path"]))
            if (ENGINEERING_DIR / f"{PIPELINE_BASE}.gds").is_file():
                return FileResponse(str(ENGINEERING_DIR / f"{PIPELINE_BASE}.gds"), filename=f"{PIPELINE_BASE}.gds")
        except Exception:
            pass
    if not gds_path or not gds_path.is_file():
        raise HTTPException(status_code=404, detail="No GDS file found. Run pipeline with --heac --gds first.")
    return FileResponse(str(gds_path), filename=gds_path.name)


@app.post("/api/apps/qrnc/mint")
def apps_qrnc_mint(req: QRNCMintRequest):
    """Mint a quantum-backed QRNC token (sim or IBM hardware)."""
    try:
        from apps.qrnc import mint_qrnc
    except Exception as e:
        raise HTTPException(status_code=503, detail=_sanitize_detail(e, "QRNC service unavailable."))
    try:
        token = mint_qrnc(
            num_bytes=req.num_bytes,
            use_real_hardware=req.use_real_hardware,
            ibm_token=req.ibm_token,
            token_id=req.token_id,
        )
        return {
            "value": token.value,
            "id": token.id,
            "issued_at": token.issued_at.isoformat() if token.issued_at else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=_sanitize_detail(e, "An internal error occurred."))


@app.post("/api/apps/qrnc/exchange")
def apps_qrnc_exchange(req: QRNCExchangeRequest):
    """Run two-party QRNC exchange (commit-then-reveal). Returns received tokens and record."""
    try:
        from apps.qrnc import QRNC, run_two_party_exchange
    except Exception as e:
        raise HTTPException(status_code=503, detail=_sanitize_detail(e, "QRNC service unavailable."))
    try:
        token_a = QRNC.from_hex(req.token_a_hex)
        token_b = QRNC.from_hex(req.token_b_hex)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid token hex.")
    try:
        received_by_a, received_by_b, record = run_two_party_exchange(
            token_a, token_b, party_a_id=req.party_a_id, party_b_id=req.party_b_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=_sanitize_detail(e, "An internal error occurred."))
    if received_by_a is None:
        return {"success": False, "message": "Verification failed"}
    return {
        "success": True,
        "received_by_a_hex": received_by_a.value,
        "received_by_b_hex": received_by_b.value,
        "record": {
            "party_a_id": record.party_a_id,
            "party_b_id": record.party_b_id,
            "timestamp": record.timestamp.isoformat(),
        },
    }


@app.post("/api/apps/bqtc/run-cycle")
def apps_bqtc_run_cycle(req: BQTCRunCycleRequest):
    """Run one BQTC pipeline cycle (no live telemetry; buffer may be empty)."""
    bqtc_dir = REPO_ROOT / "apps" / "bqtc"
    script = bqtc_dir / "run_one_cycle.py"
    if not script.is_file():
        raise HTTPException(status_code=503, detail="BQTC run_one_cycle.py not found")
    cmd = [sys.executable, str(script)]
    code, out = _run(cmd, cwd=bqtc_dir)
    if code != 0:
        raise HTTPException(status_code=503, detail=out or "BQTC run-one-cycle failed")
    try:
        data = json.loads(out) if out.strip() else []
        return {"results": data}
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=_sanitize_detail(e, "Invalid BQTC output."))


@app.post("/api/run/qkd")
def run_qkd(req: RunQKDRequest):
    """Run pedagogical QKD (BB84 or E91) in simulation."""
    try:
        if req.protocol == "bb84":
            result = _run_bb84(n_bits=req.n_bits, seed=req.seed)
        else:
            result = _run_e91(n_trials=req.n_trials, seed=req.seed)
        return result
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="QKD requires the engineering (worker) environment. Control-plane-only mode cannot run this feature.",
        )


def _run_bb84(n_bits: int, seed: int | None) -> dict:
    from src.core_compute.protocols.qkd import run_bb84
    return run_bb84(n_bits=n_bits, seed=seed)


def _run_e91(n_trials: int, seed: int | None) -> dict:
    from src.core_compute.protocols.qkd import run_e91
    return run_e91(n_trials=n_trials, seed=seed)


@app.post("/api/run/protocol")
@limit_heavy
def run_protocol(request: Request, req: RunProtocolRequest):
    """Run ASIC protocol on sim (blocking) or IBM hardware (returns job_id for WebSocket polling)."""
    use_hardware = req.backend == "hardware"
    # When engineering stack not in this process (slim API), run protocol via Celery task
    if not _engineering_available():
        if not _celery_available():
            raise HTTPException(
                status_code=503,
                detail="Celery/Redis required for protocol execution when running in control-plane-only mode (set CELERY_BROKER_URL).",
            )
        from src.backend.tasks import run_protocol_task
        task = run_protocol_task.delay(
            protocol=req.protocol,
            backend=req.backend,
            use_circuit_function=req.use_circuit_function,
            shots=1024,
        )
        try:
            result = task.get(timeout=120)
        except Exception as e:
            raise HTTPException(status_code=504, detail=_sanitize_detail(e, "Protocol task timed out or failed."))
        if result.get("error"):
            raise HTTPException(status_code=503, detail=_sanitize_detail(RuntimeError(result["error"]), "Protocol run failed."))
        if result.get("mode") == "hardware":
            from src.backend.job_store import set_job
            set_job(
                result["job_id"],
                ibm_job_id=result.get("ibm_job_id"),
                backend=result.get("backend_name", ""),
                protocol=req.protocol,
                job=None,
            )
            return {"job_id": result["job_id"], "status": "submitted", "backend": result.get("backend_name")}
        return result.get("result", {})
    if use_hardware:
        from src.core_compute.engineering.run_protocol_on_ibm import (
            submit_protocol_job,
            submit_protocol_job_via_circuit_function,
            get_ibm_job_id,
        )
        from src.backend.job_store import set_job
        try:
            if req.use_circuit_function:
                try:
                    job_id, job, backend_name = submit_protocol_job_via_circuit_function(
                        req.protocol, shots=1024
                    )
                except (ImportError, RuntimeError, Exception):
                    job_id, job, backend_name = submit_protocol_job(req.protocol, shots=1024)
            else:
                job_id, job, backend_name = submit_protocol_job(req.protocol, shots=1024)
            ibm_job_id = get_ibm_job_id(job)
            set_job(job_id, ibm_job_id=ibm_job_id, backend=backend_name or "", protocol=req.protocol, job=job)
            return {"job_id": job_id, "status": "submitted", "backend": backend_name}
        except Exception as e:
            raise HTTPException(status_code=503, detail=_sanitize_detail(e, "Protocol submission failed."))
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        out_path = f.name
    try:
        cmd = [
            sys.executable,
            str(ENGINEERING_DIR / "run_protocol_on_ibm.py"),
            "--protocol", req.protocol,
            "-o", out_path,
        ]
        code, err = _run(cmd)
        if code != 0:
            raise HTTPException(status_code=503, detail=_sanitize_detail(RuntimeError(err or "Protocol run failed"), "Protocol run failed."))
        with open(out_path, encoding="utf-8") as f:
            data = json.load(f)
        return data
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=_sanitize_detail(e, "Script or output not found."))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=_sanitize_detail(e, "Invalid output JSON."))
    finally:
        if os.path.isfile(out_path):
            try:
                os.unlink(out_path)
            except OSError:
                pass


@app.websocket("/ws/job/{job_id}")
async def websocket_job_status(websocket: WebSocket, job_id: str):
    """Stream IBM job status (QUEUED, RUNNING, DONE, ERROR) until completion. Uses Redis when set (multi-worker)."""
    await websocket.accept()
    from src.backend.job_store import get_job
    entry = get_job(job_id)
    if not entry:
        await websocket.send_json({"status": "ERROR", "error": "Unknown job_id"})
        await websocket.close()
        return
    try:
        from src.core_compute.engineering.run_protocol_on_ibm import get_job_status_and_result, get_job_status_and_result_by_ibm_job_id
    except ImportError:
        await websocket.send_json({
            "status": "ERROR",
            "error": "Job status polling requires the engineering (worker) environment. Use a deployment with the full stack for WebSocket status.",
        })
        await websocket.close()
        return
    try:
        while True:
            if "job" in entry:
                status_str, result_dict = get_job_status_and_result(entry["job"])
            elif entry.get("ibm_job_id"):
                status_str, result_dict = get_job_status_and_result_by_ibm_job_id(entry["ibm_job_id"])
            else:
                await websocket.send_json({"status": "ERROR", "error": "Missing job or ibm_job_id"})
                break
            await websocket.send_json({"status": status_str, "result": result_dict})
            if status_str in ("DONE", "ERROR"):
                break
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
    finally:
        await websocket.close()


@app.post("/api/run/routing")
@limit_heavy
def run_routing(request: Request, req: RunRoutingRequest):
    """Run QUBO routing (QAOA or RL) on sim or IBM hardware. Requires qubits when no circuit is provided."""
    if not _engineering_available():
        raise HTTPException(
            status_code=503,
            detail="Routing requires the engineering (worker) environment. Use control plane with workers or run routing via pipeline task.",
        )
    if req.qubits is None or req.qubits < 2:
        raise HTTPException(
            status_code=400,
            detail="qubits is required for standalone routing. Specify the number of qubits (2 or more), or use the Run pipeline page with an OpenQASM circuit so topology and qubit count are derived from the circuit.",
        )
    use_hardware = req.backend == "hardware"
    use_rl = (req.routing_method or "qaoa") == "rl"
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        out_path = f.name
    try:
        if use_rl:
            cmd = [
                sys.executable,
                str(ENGINEERING_DIR / "routing_rl.py"),
                "-o", out_path,
                "--qubits", str(req.qubits),
            ]
        else:
            cmd = [
                sys.executable,
                str(ENGINEERING_DIR / "routing_qubo_qaoa.py"),
                "-o", out_path,
                "--qubits", str(req.qubits),
            ]
            if use_hardware:
                cmd.append("--hardware")
            if req.fast:
                cmd.append("--fast")
            if req.topology:
                cmd.extend(["--topology", req.topology])
            if req.hub is not None and req.topology == "star":
                cmd.extend(["--hub", str(req.hub)])
        code, err = _run(cmd)
        if code != 0:
            raise HTTPException(status_code=503, detail=_sanitize_detail(RuntimeError(err or "Routing run failed"), "Routing run failed."))
        with open(out_path, encoding="utf-8") as f:
            data = json.load(f)
        return data
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=_sanitize_detail(e, "Script or output not found."))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=_sanitize_detail(e, "Invalid output JSON."))
    finally:
        if os.path.isfile(out_path):
            try:
                os.unlink(out_path)
            except OSError:
                pass


def _celery_available() -> bool:
    try:
        broker = os.environ.get("CELERY_BROKER_URL", "").strip()
        if not broker:
            return False
        from src.backend.tasks import run_pipeline_task  # noqa: F401
        return True
    except Exception:
        return False


def _engineering_available() -> bool:
    """True if the engineering stack (e.g. qiskit, qasm_to_asic) is installed in this process (data-plane / fat image)."""
    try:
        import qiskit  # noqa: F401
        return True
    except ImportError:
        return False


def _validate_qasm_string(qasm_string: str, *, decompose_to_asic: bool = False) -> None:
    """Raise HTTPException if qasm_string is invalid (length or parse). No-op on ImportError when qasm_loader not available (slim API); worker validates when task runs."""
    if len(qasm_string) > QASM_STRING_MAX_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"QASM string too long (max {QASM_STRING_MAX_LENGTH} characters)",
        )
    try:
        from src.core_compute.asic.qasm_loader import interaction_graph_from_qasm_string
        interaction_graph_from_qasm_string(qasm_string, decompose_to_asic=decompose_to_asic)
    except ImportError:
        pass  # slim API: skip validation; worker will validate when pipeline task runs
    except Exception as e:
        raise HTTPException(status_code=400, detail=_sanitize_detail(e, "Invalid QASM: parse failed"))


def _run_circuit_to_asic_sync(qasm_string: str, circuit_name: str | None, *, decompose_to_asic: bool = False) -> dict:
    """Run run_qasm_to_asic in process and return JSON-serializable result."""
    from src.backend.tasks import _circuit_to_asic_result_serializable
    from src.core_compute.engineering.qasm_to_asic_pipeline import run_qasm_to_asic
    with tempfile.TemporaryDirectory(prefix="qasic_circuit_") as tmp:
        raw = run_qasm_to_asic(
            qasm_string=qasm_string,
            output_dir=tmp,
            circuit_name=circuit_name or "circuit",
            decompose_to_asic=decompose_to_asic,
        )
        return {"success": True, "circuit_to_asic": _circuit_to_asic_result_serializable(raw)}


def _run_pipeline_with_circuit_sync(req: RunPipelineRequest) -> dict:
    """Run qasm_to_asic, then routing (circuit-derived), then run_pipeline.py --skip-routing. Returns combined result."""
    from src.backend.tasks import _circuit_to_asic_result_serializable, _routing_from_circuit_graph
    from src.core_compute.engineering.qasm_to_asic_pipeline import run_qasm_to_asic
    with tempfile.TemporaryDirectory(prefix="qasic_circuit_") as tmp:
        raw = run_qasm_to_asic(
            qasm_string=req.qasm_string,
            output_dir=tmp,
            circuit_name=req.circuit_name or "circuit",
            decompose_to_asic=req.decompose_to_asic,
        )
    graph = raw.get("_interaction_graph")
    if graph is None or graph.number_of_nodes() == 0:
        return {"success": True, "circuit_to_asic": _circuit_to_asic_result_serializable(raw), "pipeline": None}
    routing_result = _routing_from_circuit_graph(graph, fast=req.fast, hardware=req.backend.lower() == "hardware")
    routing_json_path = ENGINEERING_DIR / f"{PIPELINE_BASE}_routing.json"
    with open(routing_json_path, "w", encoding="utf-8") as f:
        json.dump(routing_result, f, indent=2)
    cmd = [sys.executable, str(ENGINEERING_DIR / "run_pipeline.py"), "-o", PIPELINE_BASE, "--skip-routing"]
    if req.fast:
        cmd.append("--fast")
    if req.model:
        cmd.extend(["--model", req.model])
    if req.heac:
        cmd.append("--heac")
        cmd.append("--gds")
    if req.backend == "hardware":
        cmd.append("--hardware")
    code, err = _run(cmd)
    if code != 0:
        raise HTTPException(status_code=503, detail=_sanitize_detail(RuntimeError(err or "Pipeline run failed"), "Pipeline with circuit failed."))
    result = {"success": True, "circuit_to_asic": _circuit_to_asic_result_serializable(raw), "routing": routing_result}
    if ROUTING_JSON.exists():
        try:
            with open(ROUTING_JSON, encoding="utf-8") as f:
                result["routing"] = json.load(f)
        except (OSError, json.JSONDecodeError):
            pass
    if INVERSE_JSON.exists():
        try:
            with open(INVERSE_JSON, encoding="utf-8") as f:
                result["inverse"] = json.load(f)
        except (OSError, json.JSONDecodeError):
            pass
    return result


def _require_project_and_circuit(req: RunPipelineRequest) -> None:
    """Require project_id and qasm_string (circuit). No defaults. Raises HTTPException 400 if missing."""
    if req.project_id is None:
        raise HTTPException(status_code=400, detail="project and circuit are required. Provide project_id.")
    qasm = (req.qasm_string or "").strip()
    if not qasm:
        raise HTTPException(status_code=400, detail="project and circuit are required. Provide a circuit (qasm_string) from the canvas.")


@app.post("/api/run/pipeline/async")
@limit_heavy
def run_pipeline_async(request: Request, req: RunPipelineRequest):
    """Enqueue pipeline run as Celery task. Requires project_id and circuit (qasm_string). No default project or circuit."""
    _require_project_and_circuit(req)
    if not _celery_available():
        raise HTTPException(status_code=503, detail="Celery/Redis not configured (set CELERY_BROKER_URL)")
    qasm = (req.qasm_string or "").strip()
    _validate_qasm_string(qasm, decompose_to_asic=req.decompose_to_asic)
    from src.backend.tasks import circuit_to_asic_task, run_pipeline_with_circuit_task
    if req.full_pipeline_with_circuit:
        task = run_pipeline_with_circuit_task.delay(
            qasm_string=qasm,
            circuit_name=req.circuit_name or "circuit",
            output_base=PIPELINE_BASE,
            fast=req.fast,
            routing_method=req.routing_method or "qaoa",
            model=req.model or "mlp",
            heac=req.heac,
            hardware=req.backend.lower() == "hardware",
            decompose_to_asic=req.decompose_to_asic,
        )
        try:
            from storage.db import record_pipeline_run, is_enabled as db_enabled
            if db_enabled():
                record_pipeline_run(
                    PIPELINE_BASE,
                    config={"backend": req.backend, "fast": req.fast, "full_pipeline_with_circuit": True},
                    task_id=task.id,
                    project_id=req.project_id,
                )
        except Exception:
            pass
        return {"task_id": task.id, "status": "PENDING", "message": "Pipeline with circuit enqueued"}
    task = circuit_to_asic_task.delay(
        qasm_string=qasm,
        circuit_name=req.circuit_name,
        decompose_to_asic=req.decompose_to_asic,
    )
    try:
        from storage.db import record_pipeline_run, is_enabled as db_enabled
        if db_enabled():
            record_pipeline_run(
                PIPELINE_BASE,
                config={"backend": req.backend, "fast": req.fast, "circuit": True},
                task_id=task.id,
                project_id=req.project_id,
            )
    except Exception:
        pass
    return {"task_id": task.id, "status": "PENDING", "message": "Circuit-to-ASIC task enqueued"}


def _is_redis_backend_error(e: Exception) -> bool:
    """True if exception is from Redis/Celery backend connection failure."""
    t = type(e)
    mod = (t.__module__ or "").lower()
    msg = str(e).lower()
    return "redis" in mod or "connection" in msg or "redis" in msg


@app.get("/api/tasks/{task_id}")
def get_task_status(task_id: str):
    """Get Celery task status and result (if ready). Returns 503 if Redis/Celery backend unavailable."""
    if not _celery_available():
        raise HTTPException(status_code=503, detail="Celery/Redis not configured")
    from src.backend.celery_app import get_celery_app
    from celery.result import AsyncResult
    try:
        celery_app = get_celery_app()
        ar = AsyncResult(task_id, app=celery_app)
        out = {"task_id": task_id, "status": ar.status}
        if ar.ready():
            if ar.successful():
                out["result"] = ar.result
            else:
                out["error"] = str(ar.result) if ar.result else "Task failed"
        return out
    except HTTPException:
        raise
    except Exception as e:
        if _is_redis_backend_error(e):
            raise HTTPException(status_code=503, detail="Celery result backend unavailable (Redis connection failed).")
        raise HTTPException(status_code=503, detail=_sanitize_detail(e, "Task status unavailable."))


@app.post("/api/tasks/{task_id}/cancel")
def cancel_task_api(task_id: str):
    """Revoke a Celery task (abort if pending or running). Returns 503 if Redis/Celery backend unavailable."""
    if not _celery_available():
        raise HTTPException(status_code=503, detail="Celery/Redis not configured")
    from src.backend.celery_app import get_celery_app
    from celery.result import AsyncResult
    try:
        celery_app = get_celery_app()
        ar = AsyncResult(task_id, app=celery_app)
        ar.revoke(terminate=True)
        return {"task_id": task_id, "message": "Cancel requested"}
    except Exception as e:
        if _is_redis_backend_error(e):
            raise HTTPException(status_code=503, detail="Celery result backend unavailable (Redis connection failed).")
        raise HTTPException(status_code=503, detail=_sanitize_detail(e, "Cancel failed."))


# Sync pipeline timeout when API enqueues and waits (slim/control-plane mode)
_PIPELINE_SYNC_WAIT_TIMEOUT = 3600


@app.post("/api/run/pipeline")
@limit_heavy
def run_pipeline(request: Request, req: RunPipelineRequest):
    """Run full pipeline. Requires project_id and circuit (qasm_string). No default project or circuit. Use /async when Celery available."""
    _require_project_and_circuit(req)
    qasm = (req.qasm_string or "").strip()
    _validate_qasm_string(qasm, decompose_to_asic=req.decompose_to_asic)
    if _celery_available() and os.environ.get("FORCE_ASYNC_HEAVY", "").strip().lower() in ("1", "true", "yes"):
        raise HTTPException(status_code=400, detail="Use POST /api/run/pipeline/async for circuit/pipeline runs (Celery worker required).")
    # When engineering stack not in this process (slim API), route through Celery and wait
    if not _engineering_available():
        if not _celery_available():
            raise HTTPException(
                status_code=503,
                detail="Celery/Redis required for pipeline execution when running in control-plane-only mode (set CELERY_BROKER_URL).",
            )
        from src.backend.tasks import circuit_to_asic_task, run_pipeline_with_circuit_task
        if req.full_pipeline_with_circuit:
            task = run_pipeline_with_circuit_task.delay(
                qasm_string=qasm,
                circuit_name=req.circuit_name or "circuit",
                output_base=PIPELINE_BASE,
                fast=req.fast,
                routing_method=req.routing_method or "qaoa",
                model=req.model or "mlp",
                heac=req.heac,
                hardware=req.backend.lower() == "hardware",
                decompose_to_asic=req.decompose_to_asic,
            )
            try:
                result = task.get(timeout=_PIPELINE_SYNC_WAIT_TIMEOUT)
                if isinstance(result, dict) and result.get("success") is False:
                    raise HTTPException(status_code=503, detail=result.get("error", "Pipeline task failed."))
                return result
            except Exception as e:
                if isinstance(e, HTTPException):
                    raise
                raise HTTPException(status_code=504, detail=_sanitize_detail(e, "Pipeline task timed out or failed."))
        task = circuit_to_asic_task.delay(
            qasm_string=qasm,
            circuit_name=req.circuit_name,
            decompose_to_asic=req.decompose_to_asic,
        )
        try:
            result = task.get(timeout=_PIPELINE_SYNC_WAIT_TIMEOUT)
            if isinstance(result, dict) and result.get("success") is False:
                raise HTTPException(status_code=503, detail=result.get("error", "Circuit-to-ASIC task failed."))
            return result
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(status_code=504, detail=_sanitize_detail(e, "Circuit-to-ASIC task timed out or failed."))
    if req.full_pipeline_with_circuit:
        result = _run_pipeline_with_circuit_sync(req)
        return result
    return _run_circuit_to_asic_sync(qasm, req.circuit_name, decompose_to_asic=req.decompose_to_asic)


@app.post("/api/run/inverse/async")
@limit_heavy
def run_inverse_async(request: Request, req: RunInverseRequest):
    """Enqueue inverse design (metasurface_inverse_net / GNN) as Celery task. Returns task_id; poll GET /api/tasks/{task_id}. Control plane stays responsive."""
    if not _celery_available():
        raise HTTPException(status_code=503, detail="Celery/Redis not configured (set CELERY_BROKER_URL)")
    routing_path = req.routing_result_path if req.routing_result_path and os.path.isfile(req.routing_result_path) else (str(ROUTING_JSON) if ROUTING_JSON.exists() else None)
    from src.backend.tasks import inverse_design_task
    task = inverse_design_task.delay(
        routing_result_path=routing_path,
        model=req.model or "mlp",
        device=req.device or "auto",
        output_base=PIPELINE_BASE,
        phase_band=req.phase_band,
    )
    return {"task_id": task.id, "status": "PENDING", "message": "Inverse design task enqueued"}


@app.post("/api/run/inverse")
@limit_heavy
def run_inverse(request: Request, req: RunInverseRequest):
    """Run inverse design (topology -> phase profile). Blocking; use /api/run/inverse/async for offload to worker."""
    if not _engineering_available():
        raise HTTPException(
            status_code=503,
            detail="Inverse design requires the engineering (worker) environment. Use /api/run/inverse/async when running in control-plane-only mode.",
        )
    if os.environ.get("FORCE_ASYNC_HEAVY", "").strip().lower() in ("1", "true", "yes") and _celery_available():
        raise HTTPException(status_code=400, detail="Use POST /api/run/inverse/async for inverse design (Celery worker required).")
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        out_path = f.name
    try:
        cmd = [
            sys.executable,
            str(ENGINEERING_DIR / "metasurface_inverse_net.py"),
            "-o", out_path,
        ]
        if req.phase_band:
            cmd.extend(["--phase-band", req.phase_band])
        if req.routing_result_path and os.path.isfile(req.routing_result_path):
            cmd.extend(["--routing-result", req.routing_result_path])
        elif ROUTING_JSON.exists():
            cmd.extend(["--routing-result", str(ROUTING_JSON)])
        code, err = _run(cmd)
        if code != 0:
            raise HTTPException(status_code=503, detail=_sanitize_detail(RuntimeError(err or "Inverse design run failed"), "Inverse design run failed."))
        with open(out_path, encoding="utf-8") as f:
            data = json.load(f)
        return data
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=_sanitize_detail(e, "Script or output not found."))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=_sanitize_detail(e, "Invalid output JSON."))
    finally:
        if os.path.isfile(out_path):
            try:
                os.unlink(out_path)
            except OSError:
                pass


def _quantum_illumination():
    from src.core_compute.protocols.quantum_illumination import entangled_probe_metrics, unentangled_probe_metrics
    return entangled_probe_metrics, unentangled_probe_metrics


@app.post("/api/run/quantum-illumination")
def run_quantum_illumination(req: QuantumIlluminationRequest):
    """Run DV quantum illumination comparison (entangled vs unentangled probe) for given eta."""
    try:
        ent_fn, unent_fn = _quantum_illumination()
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Quantum illumination requires the engineering (worker) environment. Control-plane-only mode cannot run this feature.",
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=_sanitize_detail(e, "Import failed."))
    eta = max(0.0, min(1.0, req.eta))
    try:
        ent = ent_fn(eta)
        unent = unent_fn(eta)
    except Exception as e:
        raise HTTPException(status_code=500, detail=_sanitize_detail(e, "An internal error occurred."))
    return {
        "eta": eta,
        "entangled": {"P_err": ent["P_err"], "chernoff_exponent": ent["chernoff_exponent"]},
        "unentangled": {"P_err": unent["P_err"], "chernoff_exponent": unent["chernoff_exponent"]},
        "advantage": {
            "P_err_lower_by": unent["P_err"] - ent["P_err"],
            "chernoff_higher_by": ent["chernoff_exponent"] - unent["chernoff_exponent"],
        },
    }


def _quantum_radar():
    from src.core_compute.protocols.quantum_radar import run_quantum_radar, sweep_parameter, optimize_parameter
    return run_quantum_radar, sweep_parameter, optimize_parameter


@app.post("/api/run/quantum-radar")
def run_quantum_radar_api(req: QuantumRadarRequest):
    """Run CV quantum radar (TMSV + lossy thermal BS) single point."""
    try:
        run_fn, _, _ = _quantum_radar()
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Quantum radar requires the engineering (worker) environment. Control-plane-only mode cannot run this feature.",
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=_sanitize_detail(e, "Import failed."))
    try:
        out = run_fn(eta=req.eta, n_b=max(0.0, req.n_b), r=max(0.0, req.r))
    except Exception as e:
        raise HTTPException(status_code=500, detail=_sanitize_detail(e, "An internal error occurred."))
    return out


@app.post("/api/run/quantum-radar/sweep")
def run_quantum_radar_sweep(req: QuantumRadarSweepRequest):
    """Sweep one parameter (eta, n_b, r) for CV quantum radar."""
    if req.param not in ("eta", "n_b", "r"):
        raise HTTPException(status_code=400, detail="param must be eta, n_b, or r")
    try:
        _, sweep_fn, _ = _quantum_radar()
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Quantum radar requires the engineering (worker) environment. Control-plane-only mode cannot run this feature.",
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=_sanitize_detail(e, "Import failed."))
    defaults = {"eta": (0.01, 0.5), "n_b": (0.1, 50.0), "r": (0.1, 1.5)}
    lo, hi = defaults[req.param]
    min_val = req.min_val if req.min_val is not None else lo
    max_val = req.max_val if req.max_val is not None else hi
    try:
        results = sweep_fn(req.param, min_val, max_val, req.steps, req.eta, req.n_b, req.r)
    except Exception as e:
        raise HTTPException(status_code=500, detail=_sanitize_detail(e, "An internal error occurred."))
    return {"param": req.param, "results": results}


@app.post("/api/run/quantum-radar/optimize")
def run_quantum_radar_optimize(req: QuantumRadarOptimizeRequest):
    """Optimize one parameter (eta, n_b, r) to maximize mutual_info_H1 or snr_proxy_H1."""
    if req.param not in ("eta", "n_b", "r"):
        raise HTTPException(status_code=400, detail="param must be eta, n_b, or r")
    if req.maximize not in ("mutual_info", "snr"):
        raise HTTPException(status_code=400, detail="maximize must be mutual_info or snr")
    try:
        _, _, opt_fn = _quantum_radar()
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Quantum radar requires the engineering (worker) environment. Control-plane-only mode cannot run this feature.",
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=_sanitize_detail(e, "Import failed."))
    defaults = {"eta": (0.01, 0.99), "n_b": (0.0, 100.0), "r": (0.05, 2.0)}
    lo, hi = defaults[req.param]
    low = req.optimize_min if req.optimize_min is not None else lo
    high = req.optimize_max if req.optimize_max is not None else hi
    try:
        best_val, best_result = opt_fn(req.param, low, high, req.steps, req.eta, req.n_b, req.r, req.maximize)
    except Exception as e:
        raise HTTPException(status_code=500, detail=_sanitize_detail(e, "An internal error occurred."))
    return {"best_value": best_val, "best_result": best_result}


@app.get("/api/results/latest")
def get_results_latest(project_id: int | None = None):
    """Return paths and summary of last pipeline (routing + inverse) outputs. Optional project_id for project-scoped latest."""
    routing_path = str(ROUTING_JSON)
    inverse_path = str(INVERSE_JSON)
    gds_path = None
    run_id = None
    try:
        from storage.db import get_latest_pipeline_run, is_enabled as db_enabled
        if db_enabled():
            row = get_latest_pipeline_run(project_id=project_id)
            if row:
                run_id = row.get("id")
                if row.get("routing_path"):
                    routing_path = row["routing_path"]
                if row.get("inverse_path"):
                    inverse_path = row["inverse_path"]
                gds_path = row.get("gds_path")
    except Exception:
        pass
    result = {"run_id": run_id, "routing_path": routing_path, "inverse_path": inverse_path, "gds_path": gds_path, "routing": None, "inverse": None}
    for path_key, file_path in [("routing", routing_path), ("inverse", inverse_path)]:
        if not file_path or not os.path.isfile(file_path):
            continue
        try:
            with open(file_path, encoding="utf-8") as f:
                result[path_key] = json.load(f)
        except (OSError, json.JSONDecodeError):
            pass
    return result


@app.get("/api/results/inverse-phases")
def get_inverse_phases():
    """Return phase array from latest inverse design (for 3D/2D visualization)."""
    import numpy as np
    npy_path = ENGINEERING_DIR / (PIPELINE_BASE + "_inverse_phases.npy")
    if not npy_path.is_file() and INVERSE_JSON.exists():
        try:
            with open(INVERSE_JSON, encoding="utf-8") as f:
                inv = json.load(f)
            phase_array_path = inv.get("phase_array_path")
            if phase_array_path:
                npy_path = ENGINEERING_DIR / phase_array_path
        except (OSError, json.JSONDecodeError):
            pass
    if not npy_path.is_file():
        raise HTTPException(status_code=404, detail="No inverse phase array found. Run pipeline or inverse design first.")
    try:
        arr = np.load(npy_path)
        arr = np.asarray(arr).ravel()
        n = len(arr)
        # Optionally reshape to 2D for grid display (e.g. sqrt(n) x sqrt(n))
        nx = int(np.sqrt(n))
        ny = (n + nx - 1) // nx
        if nx * ny >= n:
            arr_2d = np.zeros((nx, ny), dtype=float)
            arr_2d.ravel()[:n] = arr
            arr_2d = arr_2d.tolist()
        else:
            arr_2d = arr.reshape(1, -1).tolist()
        return {"phases": arr.tolist(), "shape": list(np.shape(np.load(npy_path))), "grid_2d": arr_2d, "grid_shape": [nx, ny]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_sanitize_detail(e, "An internal error occurred."))


# --- Deploy: generate commands for Local / VM / AWS / GCP / Azure / OpenNebula ---
DeployTargetKind = Literal["local", "vm", "aws", "gcp", "azure", "opennebula"]


class DeployGenerateRequest(BaseModel):
    target: DeployTargetKind = "local"
    aws_region: str | None = "us-east-1"


@app.post("/api/deploy/generate")
def deploy_generate(body: DeployGenerateRequest):
    """Generate deployment commands for the chosen target. Returns copy-paste commands; no execution."""
    target = body.target
    region = body.aws_region or "us-east-1"
    if target == "local":
        commands = [
            "# Core stack (API, frontend, Celery, Redis, Postgres)",
            "docker compose up -d --build",
            "# Or: make run-local-core",
            "",
            "# Full stack (+ InfluxDB, MLflow, Grafana)",
            "docker compose -f docker-compose.full.yml up -d --build",
            "# Or: make run-local",
        ]
        return {"commands": commands, "hint": "Run from the repository root."}
    if target == "aws":
        commands = [
            "# 1. Provision infra (RDS, ElastiCache, EKS)",
            "cd platform/infra/tofu",
            "tofu init",
            f'tofu apply -var="deployment_target=aws" -var="aws_region={region}"',
            "",
            "# 2. Configure kubeconfig and deploy app",
            f"aws eks update-kubeconfig --region {region} --name $(tofu output -raw eks_cluster_name)",
            "cd ../..",
            "helm upgrade --install qasic platform/deploy/helm/qasic -n qasic --create-namespace \\",
            "  --set image.registry=<your-registry>/ \\",
            "  --set image.api.repository=qasic-api --set image.frontend.repository=qasic-frontend",
        ]
        return {"commands": commands, "hint": "Ensure AWS CLI and OpenTofu are installed; run from repo root. Create ECR repos if using ECR."}
    if target == "vm":
        return {
            "commands": [
                "# VM deploy: use an existing VM with Docker installed.",
                "# From your machine, copy the repo (or clone) to the VM, then on the VM:",
                "cd qasic-engineering-as-code",
                "docker compose up -d --build",
                "",
                "# Or use the IaC Orchestrator to add a Tofu/script stage that provisions a VM and runs the above.",
            ],
            "hint": "See platform/deploy/README.md for Kubernetes on a single node; for raw VM, Docker Compose on the VM is the simplest.",
        }
    # gcp, azure, opennebula: placeholder until infra modules exist
    placeholders = {
        "gcp": ("GCP (GKE)", "deployment_target=gcp and GKE module will be added; use Helm chart on an existing GKE cluster."),
        "azure": ("Azure (AKS)", "deployment_target=azure and AKS module will be added; use Helm chart on an existing AKS cluster."),
        "opennebula": ("OpenNebula (OneKE)", "deployment_target=opennebula and OneKE module will be added; use Helm chart on an existing OneKE cluster."),
    }
    label, hint = placeholders[target]
    return {
        "commands": [f"# {label}: coming soon.", f"# {hint}", "# Same Helm chart works: platform/deploy/helm/qasic"],
        "hint": hint,
    }


@app.get("/api/docs/links")
def get_docs_links():
    """Return list of doc links for the front end."""
    links = [
        {"name": "Architecture overview", "path": "docs/app/architecture_overview.md", "url": None},
        {"name": "Quantum ASIC spec", "path": "docs/app/QUANTUM_ASIC.md", "url": None},
        {"name": "Whitepaper (Markdown)", "path": "docs/research/WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.md", "url": None},
        {"name": "Docs index", "path": "docs/app/README.md", "url": None},
        {"name": "Engineering README", "path": "src/core_compute/engineering/README.md", "url": None},
        {"name": "Channel noise & DV illumination", "path": "docs/app/CHANNEL_NOISE.md", "url": None},
        {"name": "QKD (BB84, E91)", "path": "docs/app/QKD.md", "url": None},
        {"name": "Topology builder & viz", "path": "docs/app/TOPOLOGY_BUILDER.md", "url": None},
        {"name": "CV quantum radar (TMSV)", "path": "docs/app/CV_QUANTUM_RADAR.md", "url": None},
        {"name": "EaC distributed roadmap (MD)", "path": "docs/research/Engineering_as_Code_Distributed_Computational_Roadmap.md", "url": None},
        {"name": "Cryogenic metamaterials (MD)", "path": "docs/research/Cryogenic_Metamaterial_Architectures_Quantum_SATCOM.md", "url": None},
        {"name": "Computational materials science (MD)", "path": "docs/research/Computational_Materials_Science_Cryogenic_Quantum_Metamaterials.md", "url": None},
        {"name": "Quantum terrestrial backhaul (MD)", "path": "docs/research/quantum-terrestrial-backhaul.md", "url": None},
        {"name": "Unified quantum metasurfaces SATCOM (MD)", "path": "docs/research/Whitepaper_Unified_Quantum_Metasurfaces_SATCOM.md", "url": None},
        {"name": "Infrastructure-Aware Application (IAA) whitepaper", "path": "docs/research/Whitepaper_Infrastructure_Aware_Application.md", "url": None},
        {"name": "Applications (BQTC, QRNC)", "path": "docs/app/APPLICATIONS.md", "url": None},
        {"name": "Theoretical applications", "path": "docs/app/THEORETICAL_APPLICATIONS.md", "url": None},
        {"name": "Data and control plane extensions", "path": "docs/app/DATA_AND_CONTROL_PLANE_QUANTUM_ASIC.md", "url": None},
    ]
    for L in links:
        full = REPO_ROOT / L["path"]
        L["exists"] = full.exists()
        if full.exists():
            L["url"] = f"/docs/{L['path']}"  # Front end can use relative or absolute
    return {"links": links}


_ALLOWED_DOC_PATHS = frozenset({
    "docs/README.md",
    "docs/app/architecture_overview.md",
    "docs/app/QUANTUM_ASIC.md",
    "docs/research/WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.md",
    "docs/research/Whitepaper_Unified_Quantum_Metasurfaces_SATCOM.md",
    "docs/app/README.md",
    "docs/app/CHANNEL_NOISE.md",
    "docs/app/QKD.md",
    "docs/app/TOPOLOGY_BUILDER.md",
    "docs/app/CV_QUANTUM_RADAR.md",
    "docs/research/quantum-terrestrial-backhaul.md",
    "docs/research/Engineering_as_Code_Distributed_Computational_Roadmap.md",
    "docs/research/Computational_Materials_Science_Cryogenic_Quantum_Metamaterials.md",
    "docs/research/Cryogenic_Metamaterial_Architectures_Quantum_SATCOM.md",
    "docs/research/Whitepaper_Infrastructure_Aware_Application.md",
    "src/core_compute/engineering/README.md",
    "docs/app/APPLICATIONS.md",
    "docs/app/THEORETICAL_APPLICATIONS.md",
    "docs/app/DATA_AND_CONTROL_PLANE_QUANTUM_ASIC.md",
})


@app.get("/docs/{path:path}")
def serve_doc(path: str):
    """Serve a single doc file (markdown) from the repo. Only allowed paths under docs/ or src/core_compute/engineering/README.md."""
    path = path.lstrip("/").replace("\\", "/")
    if path not in _ALLOWED_DOC_PATHS:
        raise HTTPException(status_code=404, detail="Doc not found")
    full = (REPO_ROOT / path).resolve()
    try:
        full.relative_to(REPO_ROOT.resolve())
    except ValueError:
        raise HTTPException(status_code=404, detail="Doc not found")
    if not full.is_file():
        raise HTTPException(status_code=404, detail="Doc not found")
    return FileResponse(full, media_type="text/markdown")


def _openqasm_3_available() -> bool:
    """True if qiskit.qasm3 (qiskit-qasm3-import) is importable."""
    try:
        import qiskit.qasm3  # noqa: F401
        return True
    except ImportError:
        return False


@app.get("/api/capabilities")
def get_capabilities():
    """Return backend capabilities for the WUI (e.g. OpenQASM 3.0, infrastructure features)."""
    database = False
    try:
        from storage.db import is_enabled as db_enabled
        database = db_enabled()
    except ImportError:
        pass
    mlflow = False
    try:
        from storage.artifacts_mlflow import is_enabled as mlflow_enabled
        mlflow = mlflow_enabled()
    except ImportError:
        pass
    return {
        "openqasm_3_available": _openqasm_3_available(),
        "database": database,
        "celery": _celery_available(),
        "mlflow": mlflow,
        "features": {
            "keycloak": _is_feature_enabled("keycloak"),
            "elasticache": _is_feature_enabled("elasticache"),
        },
    }


@app.get("/health")
def health():
    return {"status": "ok"}


# Serve built SPA in production (mount after routes so /api takes precedence)
FRONTEND_DIST = REPO_ROOT / "src" / "frontend" / "dist"
if FRONTEND_DIST.is_dir():
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
