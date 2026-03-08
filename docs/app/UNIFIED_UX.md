# Unified UX Implementation

This document summarizes the project-based workspace, real-time job tracking, DAG visualization, config forms, consolidated results, and unified CLI added to unify the application experience.

## 1. Project-based workspace

- **Database:** `storage/db.py` now has a `projects` table and `project_id` on `pipeline_runs`. Use `DATABASE_URL` to enable.
- **MLflow:** Each project can have an MLflow experiment; create a project via API and the backend creates `qasic-project-<name>` experiment when `MLFLOW_TRACKING_URI` is set. `storage/artifacts_mlflow.py` exposes `get_or_create_experiment()` and `log_artifact_run(..., experiment_name=...)`.
- **API:** `GET/POST /api/projects`, `GET /api/projects/{id}`, `GET /api/projects/{id}/runs`. Pipeline run endpoints accept `project_id` in the body; `GET /api/results/latest?project_id=` returns project-scoped latest.
- **Frontend:** **Projects** page lists projects and creates new ones; **Run Pipeline** has an optional project dropdown; **Results** can be scoped by `?project_id=` (e.g. from project “View results”).

## 2. Real-time job tracking (SSE + Redis)

- **Celery:** `app/tasks.py` publishes progress messages to Redis channel `qasic:task:{task_id}:log` (e.g. “Starting pipeline”, “Pipeline completed”). Requires `CELERY_BROKER_URL` (Redis).
- **API:** `GET /api/tasks/{task_id}/stream` returns Server-Sent Events. Requires `redis` with async support (`redis.asyncio`) for the SSE endpoint.
- **Frontend:** **Run Pipeline** opens an `EventSource` to the stream when a `task_id` is set and shows a live log window below the form.

## 3. Pipeline DAG visualization

- **API:** `GET /api/pipeline/dag` returns `{ nodes, edges }` for the orchestration DAG (routing, inverse_design, HEaC, GDS, DRC, LVS, thermal, etc.).
- **Frontend:** **Run Pipeline** includes a **PipelineDag** component (React Flow / `@xyflow/react`) that fetches the DAG and displays it above the form. Optional `activeStep` can highlight the current step when task status is known.

## 4. Auto-generated config forms (Pydantic → JSON Schema)

- **API:** `GET /api/schemas/pipeline` and `GET /api/schemas/thermal` return the JSON Schema of the Pydantic models (`PipelineConfig`, `ThermalConfig` from `config/loader.py`).
- **Frontend:** **Config forms** page (`/config`) uses `@rjsf/core` and `@rjsf/validator-ajv8` to render a form from the chosen schema. Users can edit values; “Submit” is client-side only (copy values or use as reference for run parameters / YAML).

## 5. Consolidated results dashboard

- **API:** `GET /api/results/latest` now returns `run_id`, `gds_path`, and optional `project_id`. `GET /api/results/gds` serves the latest (or given `output_base`) GDS file for download. `GET /api/mlflow/runs?experiment_id=` proxies MLflow runs for the default or project experiment.
- **Frontend:** **Results** page is a single pane: Phase Viewer (3D) embed, MLflow runs table (when MLflow is configured), **Download GDS** button when `gds_path` is present, plus existing Routing and Inverse sections.

## 6. Unified CLI (Typer)

- **Entry point:** Root `cli.py` with Typer. Install with `pip install -e ".[cli]"` (adds `typer`). Entry point: `qasic = "cli:cli"` in `pyproject.toml`.
- **Commands:**
  - `qasic run-pipeline` — runs `engineering/run_pipeline.py` with options (`--config`, `-o`, `--fast`, `--routing-method`, `--model`, `--heac`, etc.).
  - `qasic view-results [--job-id TASK_ID] [--project-id ID]` — shows latest run from DB or task status from API (`QASIC_API_BASE`).
  - `qasic serve [--host] [--port] [--reload]` — starts the FastAPI app with uvicorn.
  - `qasic project create NAME [--description DESC]` — creates a project (requires `DATABASE_URL`).
  - `qasic project list` — lists projects.

## Quick start (unified flow)

1. **Backend:** Set `DATABASE_URL`, optionally `MLFLOW_TRACKING_URI` and `CELERY_BROKER_URL`. Run migrations by starting the API once (tables/columns created in `storage/db.py`).
2. **Create a project:** In the UI (**Projects** → New project) or CLI: `qasic project create "Quantum Radar Metasurface"`.
3. **Run pipeline:** In **Run Pipeline**, select the project (optional), click Run. Use the live log and DAG; when Celery is used, progress is streamed via SSE.
4. **Results:** Open **Results** (or **Results?project_id=1** from a project). View phase viewer, MLflow runs, and download GDS from one screen.
5. **CLI:** `qasic run-pipeline --fast`, then `qasic view-results`, or `qasic serve` to start the web app.
