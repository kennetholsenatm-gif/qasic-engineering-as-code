# QASIC Engineering-as-Code – API backend

FastAPI server that exposes runs for protocol, routing, pipeline, and inverse design, plus latest results and doc links.

## Setup

From **repo root** (required so protocol/routing/pipeline subprocesses and imports resolve correctly):

```bash
pip install -r requirements.txt
pip install -r app/requirements.txt
```

Optional: install [engineering/requirements-engineering.txt](../engineering/requirements-engineering.txt) so routing and inverse design have Qiskit and PyTorch. For IBM hardware runs, set `IBM_QUANTUM_TOKEN`.

**Runtime deps:** The API runs protocol, routing, and pipeline by subprocess and by importing `protocols`, `state`, etc. Start the server from the repository root and ensure base `requirements.txt` (and optionally engineering deps) are installed so those imports and subprocess calls succeed.

## Run

From repo root:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then open http://localhost:8000/docs for Swagger UI, or point the front end at http://localhost:8000.

## Endpoints

- `POST /api/run/protocol` — body: `{ "protocol": "teleport"|"bell"|"commitment"|"thief", "backend": "sim"|"hardware" }`
- `POST /api/run/routing` — body: `{ "backend", "fast", "topology", "qubits", "hub", "routing_method": "qaoa"|"rl" }`
- `POST /api/run/pipeline` — body: `{ "backend", "fast", "routing_method", "model": "mlp"|"gnn", "heac", "skip_routing", "skip_inverse" }` (synchronous)
- `POST /api/run/pipeline/async` — same body; enqueues pipeline as Celery task, returns `{ "task_id", "status": "PENDING" }` (requires Redis + Celery worker)
- `POST /api/run/inverse/async` — body: `{ "phase_band", "routing_result_path", "model", "device" }`; enqueues inverse design (metasurface_inverse_net / GNN) as Celery task, returns `task_id` for polling
- `GET /api/tasks/{task_id}` — Celery task status and result (when ready). Used by dashboard after calling pipeline/async or inverse/async.
- `POST /api/run/inverse` — body: `{ "phase_band": "pi"|null, "routing_result_path": null|"..." }` (blocking; use inverse/async when workers are available)
- `GET /api/results/latest` — last pipeline routing + inverse summary
- `GET /api/docs/links` — list of doc links for the UI
- `GET /health` — health check

## Async tasks (Celery + Redis)

For non-blocking pipeline (and future MEEP/inverse) runs, set a broker and run a worker:

1. **Redis** (broker and result backend):  
   - Install and start Redis (e.g. `redis-server` or Docker).  
   - Set `CELERY_BROKER_URL=redis://localhost:6379/0` and optionally `CELERY_RESULT_BACKEND=redis://localhost:6379/0`.

2. **Celery worker** (from repo root, with app deps installed):  
   ```bash
   celery -A app.celery_app worker -l info
   ```
   Use `get_celery_app()` from `app.celery_app` (broker/backend read from the env above).

3. **Usage:**  
   - `POST /api/run/pipeline/async` returns `task_id`.  
   - Poll `GET /api/tasks/{task_id}` for `status` and `result` (or `error` on failure).  
   If Redis/Celery are not configured, the async endpoint returns 503.
