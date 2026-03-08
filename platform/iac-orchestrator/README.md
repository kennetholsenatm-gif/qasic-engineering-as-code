# IaC Orchestrator

**Infra pipelines only.** Pipeline-style DAG UI for **Infrastructure as Code:** define deployment pipelines (e.g. Tofu init → plan → approval → apply) in a visual graph and run them so that OpenTofu (or scripts) execute in order.

**Relationship to the main app:** The main QASIC application uses a **Hybrid Compute Dispatcher** (in `src/backend/dispatcher.py` and `executor.py`) to run *engineering* DAGs: routing, inverse design, protocols, quantum illumination, etc. That orchestrator is integrated into the main web app and Celery. *This* tool is **only for IaC pipelines** (OpenTofu, custom scripts, approval gates). It does *not* run the engineering pipeline; for that use the main app’s Run Pipeline / Workflows or `src/core_compute/engineering/run_pipeline.py`. To chain infra with the EaC pipeline, add a **Script** stage that runs `python -m src.core_compute.engineering.run_pipeline` (or `run_pipeline.py --use-orchestrator`) from repo root.

## Features

- **DAG UI:** Drag-and-drop pipeline stages (React Flow). Stages: Tofu init, Tofu plan, Tofu apply, Tofu destroy, Approval, Script.
- **Execution:** Runs stages in topological order. Tofu stages run `tofu init` / `plan` / `apply` in a configured directory (e.g. `infra/tofu`). Approval stages pause until you approve via the API.
- **Standalone:** Runs independently from the main QASIC app. No changes to the main API or frontend.

## Quick start

### Option A: Docker Compose (from repo root)

From the **repository root**:

```bash
docker compose -f platform/iac-orchestrator/docker-compose.yml up -d --build
```

Then open **http://localhost:8080**. The backend (port 8001) has the repo root mounted at `/repo`, so Tofu stages can run against `platform/infra/tofu` (set **Tofu root** in the stage config to `platform/infra/tofu` or `infra/tofu` if running from repo root with that layout).

### Option B: Local dev

**Backend:**

```bash
cd platform/iac-orchestrator
pip install -r backend/requirements.txt
# From repo root so platform/infra/tofu is available (or set IAC_ORCHESTRATOR_REPO_ROOT)
export IAC_ORCHESTRATOR_REPO_ROOT=/path/to/qasic-engineering-as-code
uvicorn backend.main:app --host 0.0.0.0 --port 8001
```

**Frontend:** (UI was merged into the main app at `src/frontend`; this tool runs headless or use the main app’s Deploy / Pipelines if linked.)

Open http://localhost:5174 (Vite proxies `/api` to the backend).

## Define a pipeline

1. Add nodes from the **Stage types** palette (e.g. Tofu init → Tofu plan → Approval → Tofu apply).
2. Connect them with edges (execution order).
3. **Save** the pipeline (give it a name).
4. **Run** to execute. View run history and per-stage stdout/stderr below the canvas.

## Stage config

- **Tofu stages:** Set **Tofu root** (e.g. `infra/tofu`), optional **workspace**, **var file**, or **vars** (key-value).
- **Script:** Set **script_path** and optional **script_args** (command to run; runs from repo root when using Docker). To run the EaC pipeline after infra apply, use e.g. `script_path` = `python` and `script_args` = `-m src.core_compute.engineering.run_pipeline --use-orchestrator` (or a shell script that invokes it).
- **Approval:** No config; the run pauses until you call `POST /api/runs/{run_id}/approve/{node_id}` with `{"approved": true}` or `false`.

## API

- `GET /api/stage-types` — List stage types for the palette.
- `GET/POST/PUT /api/pipelines` — List, create, update pipelines.
- `POST /api/pipelines/{id}/run` — Start a run.
- `GET /api/runs/{id}` — Run status and per-stage logs.
- `POST /api/runs/{id}/approve/{node_id}` — Approve or reject an approval stage.

Open http://localhost:8001/docs when the backend is running for the full OpenAPI spec.

## Layout

```
platform/iac-orchestrator/
├── README.md           # This file
├── docker-compose.yml  # Backend; mount repo at /repo
├── Dockerfile.backend # FastAPI + OpenTofu
├── backend/
│   ├── main.py        # FastAPI app, pipeline CRUD, run, approve
│   ├── models.py      # Pydantic: pipeline, run, stage config
│   ├── storage.py     # In-memory pipelines and runs
│   └── executor.py    # Topological run; Tofu / script / approval (IaC only)
```

The frontend for this tool was merged into the main app (`src/frontend`); the main app’s FBP canvas and Deploy page can link to this backend for IaC-only pipelines. The main repo’s **platform/infra/tofu** is not modified; the orchestrator only **invokes** it when you run Tofu stages.
