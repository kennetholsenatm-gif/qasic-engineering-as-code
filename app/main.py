"""
FastAPI backend for QASIC Engineering-as-Code.
Provides API routes to run protocol, routing, pipeline, inverse design,
quantum illumination, quantum radar; return latest results and doc links.
Run with: uvicorn app.main:app --reload
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
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

# IBM protocol jobs: Redis-backed when CELERY_BROKER_URL set (multi-worker); else in-memory (single-worker)
# Use app.job_store.get_job / set_job

REPO_ROOT = Path(__file__).resolve().parents[1]
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


class RunRoutingRequest(BaseModel):
    backend: BackendKind = "sim"
    fast: bool = False
    topology: TopologyKind | None = None
    qubits: int | None = None
    hub: int | None = None
    routing_method: RoutingMethodKind | None = None


class RunPipelineRequest(BaseModel):
    backend: BackendKind = "sim"
    fast: bool = False
    routing_method: RoutingMethodKind | None = None
    model: ModelKind | None = None
    heac: bool = False
    skip_routing: bool = False
    skip_inverse: bool = False
    project_id: int | None = None


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


@app.get("/api/dag/task-types")
def get_dag_task_types():
    """Return task type registry for palette and validation (inputs, outputs, backends)."""
    try:
        from orchestration.task_registry import list_task_types
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
        from orchestration.dag_validate import validate_dag
        errors = validate_dag(req.nodes, req.edges)
        return {"valid": len(errors) == 0, "errors": errors}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_sanitize_detail(e, "Validation failed."))


@app.post("/api/dag/{dag_id}/run")
@limit_heavy
def run_dag_api(request: Request, dag_id: int):
    """Create a DAG run and enqueue execution (Celery). Returns run_id and task_id when Celery available."""
    try:
        from storage.db import get_dag, create_dag_run, update_dag_run, is_enabled
        if not is_enabled():
            raise HTTPException(status_code=503, detail="Database not configured (set DATABASE_URL).")
        d = get_dag(dag_id)
        if not d:
            raise HTTPException(status_code=404, detail="DAG not found.")
        nodes = d.get("nodes") or []
        edges = d.get("edges") or []
        run_id = create_dag_run(dag_id=dag_id, status="pending", nodes_snapshot=nodes, edges_snapshot=edges)
        if run_id is None:
            raise HTTPException(status_code=500, detail="Failed to create run.")
        task_id = None
        if _celery_available():
            from app.tasks import run_dag_task
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
    if req.protocol == "bb84":
        result = _run_bb84(n_bits=req.n_bits, seed=req.seed)
    else:
        result = _run_e91(n_trials=req.n_trials, seed=req.seed)
    return result


def _run_bb84(n_bits: int, seed: int | None) -> dict:
    from protocols.qkd import run_bb84
    return run_bb84(n_bits=n_bits, seed=seed)


def _run_e91(n_trials: int, seed: int | None) -> dict:
    from protocols.qkd import run_e91
    return run_e91(n_trials=n_trials, seed=seed)


@app.post("/api/run/protocol")
@limit_heavy
def run_protocol(request: Request, req: RunProtocolRequest):
    """Run ASIC protocol on sim (blocking) or IBM hardware (returns job_id for WebSocket polling)."""
    use_hardware = req.backend == "hardware"
    if use_hardware:
        try:
            from engineering.run_protocol_on_ibm import submit_protocol_job, get_ibm_job_id
            from app.job_store import set_job
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
    from app.job_store import get_job
    entry = get_job(job_id)
    if not entry:
        await websocket.send_json({"status": "ERROR", "error": "Unknown job_id"})
        await websocket.close()
        return
    from engineering.run_protocol_on_ibm import get_job_status_and_result, get_job_status_and_result_by_ibm_job_id
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
    """Run QUBO routing (QAOA or RL) on sim or IBM hardware."""
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
                "--qubits", str(req.qubits if req.qubits is not None else 3),
            ]
        else:
            cmd = [
                sys.executable,
                str(ENGINEERING_DIR / "routing_qubo_qaoa.py"),
                "-o", out_path,
            ]
            if use_hardware:
                cmd.append("--hardware")
            if req.fast:
                cmd.append("--fast")
            if req.topology:
                cmd.extend(["--topology", req.topology])
            if req.qubits is not None:
                cmd.extend(["--qubits", str(req.qubits)])
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
        from app.tasks import run_pipeline_task
        return True
    except Exception:
        return False


@app.post("/api/run/pipeline/async")
@limit_heavy
def run_pipeline_async(request: Request, req: RunPipelineRequest):
    """Enqueue pipeline run as Celery task. Returns task_id; poll GET /api/tasks/{task_id} for status. Requires CELERY_BROKER_URL (e.g. redis)."""
    if not _celery_available():
        raise HTTPException(status_code=503, detail="Celery/Redis not configured (set CELERY_BROKER_URL)")
    if log:
        log.info("Enqueueing pipeline task", fast=req.fast, routing_method=req.routing_method or "qaoa", model=req.model or "mlp", heac=req.heac)
    from app.tasks import run_pipeline_task
    task = run_pipeline_task.delay(
        output_base=PIPELINE_BASE,
        fast=req.fast,
        routing_method=req.routing_method or "qaoa",
        model=req.model or "mlp",
        heac=req.heac,
        skip_routing=req.skip_routing,
        skip_inverse=req.skip_inverse,
        hardware=req.backend.lower() == "hardware",
    )
    try:
        from storage.db import record_pipeline_run, is_enabled as db_enabled
        if db_enabled():
            record_pipeline_run(
                PIPELINE_BASE,
                config={"backend": req.backend, "fast": req.fast, "routing_method": req.routing_method, "model": req.model, "heac": req.heac},
                task_id=task.id,
                project_id=req.project_id,
            )
    except Exception:
        pass
    return {"task_id": task.id, "status": "PENDING", "message": "Pipeline task enqueued"}


@app.get("/api/tasks/{task_id}")
def get_task_status(task_id: str):
    """Get Celery task status and result (if ready)."""
    if not _celery_available():
        raise HTTPException(status_code=503, detail="Celery/Redis not configured")
    from app.celery_app import get_celery_app
    from celery.result import AsyncResult
    celery_app = get_celery_app()
    ar = AsyncResult(task_id, app=celery_app)
    out = {"task_id": task_id, "status": ar.status }
    if ar.ready():
        if ar.successful():
            out["result"] = ar.result
        else:
            out["error"] = str(ar.result) if ar.result else "Task failed"
    return out


@app.post("/api/run/pipeline")
@limit_heavy
def run_pipeline(request: Request, req: RunPipelineRequest):
    """Run full pipeline: routing then inverse design. Optional: routing_method, model, heac. Use /async when Celery available."""
    if os.environ.get("FORCE_ASYNC_HEAVY", "").strip().lower() in ("1", "true", "yes") and _celery_available():
        raise HTTPException(status_code=400, detail="Use POST /api/run/pipeline/async for pipeline runs (Celery worker required).")
    run_id = None
    try:
        from storage.db import record_pipeline_run, update_pipeline_run, is_enabled as db_enabled
        if db_enabled():
            run_id = record_pipeline_run(
                PIPELINE_BASE,
                config={"backend": req.backend, "fast": req.fast, "routing_method": req.routing_method, "model": req.model, "heac": req.heac},
                project_id=req.project_id,
            )
    except Exception:
        pass
    cmd = [sys.executable, str(ENGINEERING_DIR / "run_pipeline.py")]
    if req.backend == "hardware":
        cmd.append("--hardware")
    if req.fast:
        cmd.append("--fast")
    if req.routing_method:
        cmd.extend(["--routing-method", req.routing_method])
    if req.model:
        cmd.extend(["--model", req.model])
    if req.heac:
        cmd.append("--heac")
    if req.skip_routing:
        cmd.append("--skip-routing")
    if req.skip_inverse:
        cmd.append("--skip-inverse")
    code, err = _run(cmd)
    if code != 0:
        if run_id is not None:
            try:
                from storage.db import update_pipeline_run
                update_pipeline_run(run_id=run_id, status="failed", error_message=err or "Pipeline run failed")
            except Exception:
                pass
        raise HTTPException(status_code=503, detail=_sanitize_detail(RuntimeError(err or "Pipeline run failed"), "Pipeline run failed."))
    try:
        from storage.db import update_pipeline_run
        gds_path_str = str(ENGINEERING_DIR / f"{PIPELINE_BASE}.gds") if (ENGINEERING_DIR / f"{PIPELINE_BASE}.gds").exists() else None
        update_pipeline_run(
            run_id=run_id,
            status="success",
            routing_path=str(ROUTING_JSON) if ROUTING_JSON.exists() else None,
            inverse_path=str(INVERSE_JSON) if INVERSE_JSON.exists() else None,
            gds_path=gds_path_str,
        )
    except Exception:
        pass
    result = {"message": "Pipeline completed", "routing_json": str(ROUTING_JSON), "inverse_json": str(INVERSE_JSON)}
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


@app.post("/api/run/inverse/async")
@limit_heavy
def run_inverse_async(request: Request, req: RunInverseRequest):
    """Enqueue inverse design (metasurface_inverse_net / GNN) as Celery task. Returns task_id; poll GET /api/tasks/{task_id}. Control plane stays responsive."""
    if not _celery_available():
        raise HTTPException(status_code=503, detail="Celery/Redis not configured (set CELERY_BROKER_URL)")
    routing_path = req.routing_result_path if req.routing_result_path and os.path.isfile(req.routing_result_path) else (str(ROUTING_JSON) if ROUTING_JSON.exists() else None)
    from app.tasks import inverse_design_task
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
    from protocols.quantum_illumination import entangled_probe_metrics, unentangled_probe_metrics
    return entangled_probe_metrics, unentangled_probe_metrics


@app.post("/api/run/quantum-illumination")
def run_quantum_illumination(req: QuantumIlluminationRequest):
    """Run DV quantum illumination comparison (entangled vs unentangled probe) for given eta."""
    try:
        ent_fn, unent_fn = _quantum_illumination()
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
    from protocols.quantum_radar import run_quantum_radar, sweep_parameter, optimize_parameter
    return run_quantum_radar, sweep_parameter, optimize_parameter


@app.post("/api/run/quantum-radar")
def run_quantum_radar_api(req: QuantumRadarRequest):
    """Run CV quantum radar (TMSV + lossy thermal BS) single point."""
    try:
        run_fn, _, _ = _quantum_radar()
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


@app.get("/api/docs/links")
def get_docs_links():
    """Return list of doc links for the front end."""
    links = [
        {"name": "Architecture overview", "path": "docs/architecture_overview.md", "url": None},
        {"name": "Quantum ASIC spec", "path": "docs/QUANTUM_ASIC.md", "url": None},
        {"name": "Whitepaper (Markdown)", "path": "docs/WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.md", "url": None},
        {"name": "Docs index", "path": "docs/README.md", "url": None},
        {"name": "Engineering README", "path": "engineering/README.md", "url": None},
        {"name": "Channel noise & DV illumination", "path": "docs/CHANNEL_NOISE.md", "url": None},
        {"name": "QKD (BB84, E91)", "path": "docs/QKD.md", "url": None},
        {"name": "Topology builder & viz", "path": "docs/TOPOLOGY_BUILDER.md", "url": None},
        {"name": "CV quantum radar (TMSV)", "path": "docs/CV_QUANTUM_RADAR.md", "url": None},
        {"name": "EaC distributed roadmap (MD)", "path": "docs/Engineering_as_Code_Distributed_Computational_Roadmap.md", "url": None},
        {"name": "Cryogenic metamaterials (MD)", "path": "docs/Cryogenic_Metamaterial_Architectures_Quantum_SATCOM.md", "url": None},
        {"name": "Computational materials science (MD)", "path": "docs/Computational_Materials_Science_Cryogenic_Quantum_Metamaterials.md", "url": None},
        {"name": "Quantum terrestrial backhaul (MD)", "path": "docs/quantum-terrestrial-backhaul.md", "url": None},
        {"name": "Unified quantum metasurfaces SATCOM (MD)", "path": "docs/Whitepaper_Unified_Quantum_Metasurfaces_SATCOM.md", "url": None},
        {"name": "Applications (BQTC, QRNC)", "path": "docs/APPLICATIONS.md", "url": None},
        {"name": "Data and control plane extensions", "path": "docs/DATA_AND_CONTROL_PLANE_QUANTUM_ASIC.md", "url": None},
    ]
    for L in links:
        full = REPO_ROOT / L["path"]
        L["exists"] = full.exists()
        if full.exists():
            L["url"] = f"/docs/{L['path']}"  # Front end can use relative or absolute
    return {"links": links}


_ALLOWED_DOC_PATHS = frozenset({
    "docs/architecture_overview.md",
    "docs/QUANTUM_ASIC.md",
    "docs/WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.md",
    "docs/Whitepaper_Unified_Quantum_Metasurfaces_SATCOM.md",
    "docs/README.md",
    "docs/CHANNEL_NOISE.md",
    "docs/QKD.md",
    "docs/TOPOLOGY_BUILDER.md",
    "docs/CV_QUANTUM_RADAR.md",
    "docs/quantum-terrestrial-backhaul.md",
    "docs/Engineering_as_Code_Distributed_Computational_Roadmap.md",
    "docs/Computational_Materials_Science_Cryogenic_Quantum_Metamaterials.md",
    "docs/Cryogenic_Metamaterial_Architectures_Quantum_SATCOM.md",
    "engineering/README.md",
    "docs/APPLICATIONS.md",
    "docs/DATA_AND_CONTROL_PLANE_QUANTUM_ASIC.md",
})


@app.get("/docs/{path:path}")
def serve_doc(path: str):
    """Serve a single doc file (markdown) from the repo. Only allowed paths under docs/ or engineering/README.md."""
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


@app.get("/health")
def health():
    return {"status": "ok"}


# Serve built SPA in production (mount after routes so /api takes precedence)
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"
if FRONTEND_DIST.is_dir():
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
