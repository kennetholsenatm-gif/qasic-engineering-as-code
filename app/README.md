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
- `POST /api/run/pipeline` — body: `{ "backend", "fast", "routing_method", "model": "mlp"|"gnn", "heac", "skip_routing", "skip_inverse" }`
- `POST /api/run/inverse` — body: `{ "phase_band": "pi"|null, "routing_result_path": null|"..." }`
- `GET /api/results/latest` — last pipeline routing + inverse summary
- `GET /api/docs/links` — list of doc links for the UI
- `GET /health` — health check
