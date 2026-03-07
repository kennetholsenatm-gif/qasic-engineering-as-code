# QASIC Engineering-as-Code – API backend

FastAPI server that exposes runs for protocol, routing, pipeline, and inverse design, plus latest results and doc links.

## Setup

From repo root:

```bash
pip install -r app/requirements.txt
```

Optional: install [engineering/requirements-engineering.txt](../engineering/requirements-engineering.txt) so routing and protocol runs have Qiskit and PyTorch. For IBM hardware runs, set `IBM_QUANTUM_TOKEN`.

## Run

From repo root:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then open http://localhost:8000/docs for Swagger UI, or point the front end at http://localhost:8000.

## Endpoints

- `POST /api/run/protocol` — body: `{ "protocol": "teleport"|"bell"|"commitment"|"thief", "backend": "sim"|"hardware" }`
- `POST /api/run/routing` — body: `{ "backend": "sim"|"hardware", "fast": true|false }`
- `POST /api/run/pipeline` — body: `{ "backend": "sim"|"hardware", "fast": false }`
- `POST /api/run/inverse` — body: `{ "phase_band": "pi"|null, "routing_result_path": null|"..." }`
- `GET /api/results/latest` — last pipeline routing + inverse summary
- `GET /api/docs/links` — list of doc links for the UI
- `GET /health` — health check
