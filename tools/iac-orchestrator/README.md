# IaC Orchestrator

**Infra pipelines only.** Pipeline-style DAG UI for **Infrastructure as Code:** define deployment pipelines (e.g. Tofu init → plan → approval → apply) in a visual graph and run them so that OpenTofu (or scripts) execute in order. This tool does *not* run the Engineering pipeline (routing → inverse → HEaC); for that use `engineering/run_pipeline.py` or the main app’s Run Pipeline / Workflows. To chain infra with the EaC pipeline, add a **Script** stage that runs `engineering/run_pipeline.py --use-orchestrator` (e.g. from repo root).

## Features

- **DAG UI:** Drag-and-drop pipeline stages (React Flow). Stages: Tofu init, Tofu plan, Tofu apply, Tofu destroy, Approval, Script.
- **Execution:** Runs stages in topological order. Tofu stages run `tofu init` / `plan` / `apply` in a configured directory (e.g. `infra/tofu`). Approval stages pause until you approve via the API.
- **Standalone:** Runs independently from the main QASIC app. No changes to the main API or frontend.

## Quick start

### Option A: Docker Compose (from repo root)

From the **repository root**:

```bash
docker compose -f tools/iac-orchestrator/docker-compose.yml up -d --build
```

Then open **http://localhost:8080**. The backend (port 8001) has the repo root mounted at `/repo`, so Tofu stages can run against `infra/tofu` (set **Tofu root** in the stage config to `infra/tofu`).

### Option B: Local dev

**Backend:**

```bash
cd tools/iac-orchestrator
pip install -r backend/requirements.txt
# From repo root so infra/tofu is available (or set IAC_ORCHESTRATOR_REPO_ROOT)
export IAC_ORCHESTRATOR_REPO_ROOT=/path/to/qasic-engineering-as-code
uvicorn backend.main:app --host 0.0.0.0 --port 8001
```

**Frontend:**

```bash
cd tools/iac-orchestrator/frontend
npm install
npm run dev
```

Open http://localhost:5174 (Vite proxies `/api` to the backend).

## Define a pipeline

1. Add nodes from the **Stage types** palette (e.g. Tofu init → Tofu plan → Approval → Tofu apply).
2. Connect them with edges (execution order).
3. **Save** the pipeline (give it a name).
4. **Run** to execute. View run history and per-stage stdout/stderr below the canvas.

## Stage config

- **Tofu stages:** Set **Tofu root** (e.g. `infra/tofu`), optional **workspace**, **var file**, or **vars** (key-value).
- **Script:** Set **script_path** and optional **script_args** (command to run; runs from repo root when using Docker). To run the EaC pipeline after infra apply, use e.g. `script_path` = `engineering/run_pipeline.py` and `script_args` = `--use-orchestrator` (or a shell script that invokes it).
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
tools/iac-orchestrator/
├── README.md           # This file
├── docker-compose.yml  # Backend + frontend; mount repo at /repo
├── Dockerfile.backend # FastAPI + OpenTofu
├── Dockerfile.frontend
├── backend/
│   ├── main.py        # FastAPI app, pipeline CRUD, run, approve
│   ├── models.py      # Pydantic: pipeline, run, stage config
│   ├── storage.py     # In-memory pipelines and runs
│   └── executor.py    # Topological run; Tofu / script / approval
└── frontend/
    ├── src/
    │   ├── pages/Pipelines.jsx   # DAG canvas, palette, save/load, run
    │   └── components/StageNode.jsx
    ├── package.json
    └── vite.config.js
```

The main repo’s **infra/tofu** is not modified; the orchestrator only **invokes** it when you run Tofu stages.
