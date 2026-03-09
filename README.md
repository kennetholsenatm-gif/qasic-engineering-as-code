# QASIC Engineering-as-Code

**Repository:** [github.com/kennetholsenatm-gif/qasic-engineering-as-code](https://github.com/kennetholsenatm-gif/qasic-engineering-as-code)

**Quantum ASIC and Engineering-as-Code (EaC):** protocols, routing, inverse design, quantum illumination, and CV quantum radar—with a **web app** for flow-based workflows, deployment, and hybrid compute.

---

## The QASIC app

The main way to use the stack is the **QASIC web app**: FastAPI backend, React frontend, and a **Hybrid Compute Dispatcher** that runs your DAGs on the right resource (classical sim, FDTD-style engineering, or quantum backend).

| Feature | Description |
|--------|--------------|
| **Flow-based workflow (FBP)** | **Workflows** page: drag-and-drop task types from the Task Registry onto a canvas, connect edges to form a DAG, then **Deploy / Run**. Task types (protocols, routing, inverse design, etc.) show a compute badge (Sim, FDTD, QPU, EKS). |
| **Hybrid DAG orchestrator** | Backend parses each node, resolves compute resource via `dispatcher.py`, and routes jobs to local executor, IBM Quantum, or (future) EKS. See [src/backend/README.md](src/backend/README.md). |
| **Deploy** | **Deploy** page: pick a target (Local, VM, AWS, GCP, Azure, OpenNebula) and get generated commands (Docker Compose, OpenTofu, Helm). For full infra DAG control, use the **IaC Orchestrator** under `platform/iac-orchestrator/`. |
| **Run Pipeline** | Fixed metasurface pipeline (routing → inverse design → HEaC → GDS → DRC/LVS) as a read-only DAG view; run from the app or CLI. |

---

## Running the stack

### Docker (recommended)

**Quick start** (clone, configure, run):

```bash
git clone https://github.com/kennetholsenatm-gif/qasic-engineering-as-code.git
cd qasic-engineering-as-code
# Create .env from example (Windows: copy .env.example .env | Mac/Linux: cp .env.example .env)
docker compose up -d --build
```

- **What you get:** Web UI (frontend), API, Celery worker, Redis, and Postgres. This is the full WUI experience: Run Pipeline, Workflows, Projects, async task streaming, and Results. The API image is built with `.[app,engineering]`, so **OpenQASM 3.0** (via `qiskit-qasm3-import`), routing, and HEaC are included—no extra install for circuit-to-ASIC in the app.
- **Environment:** The core stack sets `DATABASE_URL`, `CELERY_BROKER_URL`, and Postgres inside `docker-compose.yml`; you do not need to edit `.env` for a basic run. Copying `.env.example` to `.env` is only so the file exists. Optionally set `IBM_QUANTUM_TOKEN` in `.env` if you use IBM Quantum from the app.

Open the frontend at **http://localhost** (port 80). API docs: **http://localhost:8000/docs**.

**Port 80 in use or blocked?** (common on Windows with IIS or macOS with Apache)  
- Edit `docker-compose.yml`: under the `frontend` service, change `ports` from `"80:8080"` to `"8080:8080"`.  
- Run `docker compose up -d --build` again, then open **http://localhost:8080**.

**If you see ERR_CONNECTION_REFUSED on http://localhost:**  
- Ensure Docker is running and the stack is up: `docker compose ps` (all services should be “Up”). If not, run `docker compose up -d --build` from the repo root and wait ~30s for the API healthcheck to pass.  
- If port 80 is in use, use the port change above and **http://localhost:8080**.

**More services (dashboards, MLflow):**  
- **Full stack** (core + InfluxDB, MLflow, Grafana): `docker compose -f docker-compose.full.yml up -d --build` or `make run-local`. Use this if you want experiment tracking and Grafana dashboards in addition to the Web UI.  
- **Jupyter**: `docker compose --profile jupyter run --service-ports jupyter`.

### Platform: Helm and OpenTofu

For production, use **Kubernetes** and the Helm chart under [platform/deploy/](platform/deploy/). Provision infra (e.g. AWS EKS, RDS, ElastiCache) with OpenTofu in [platform/infra/tofu/](platform/infra/tofu/). The app’s **Deploy** page generates the exact commands; see [platform/deploy/README.md](platform/deploy/README.md).

---

## Installation and quick start (dev)

**Prerequisites:** Python 3.10+ (use `py` or `python` as on your system). For the web app frontend you also need **Node.js 18+** and **npm**.

Run from **repo root**:

```bash
git clone https://github.com/kennetholsenatm-gif/qasic-engineering-as-code.git
cd qasic-engineering-as-code
pip install -e .
```

**Demos** (protocols and ASIC; no app required):

```bash
python demos/demo_teleport.py
python demos/demo_thief.py
python demos/demo_commitment.py
python demos/demo_asic.py
```

**Web app** (backend + frontend, no Docker):

```bash
pip install -e ".[app]"
# Terminal 1 – backend:
uvicorn src.backend.main:app --reload
# Terminal 2 – frontend (requires Node.js and npm):
cd src/frontend && npm install && npm run dev
```

Then open **http://localhost:5173** (Vite dev server). The API is at **http://localhost:8000**. See [src/frontend/README.md](src/frontend/README.md) for frontend details.

**Note:** This path does not start Celery, Redis, or Postgres. The UI will load, but pipeline runs use the **synchronous** API (no live task log or Stop button), and project workspaces / MLflow integration are unavailable. For the full WUI (async runs, projects, task streaming), use Docker above.

**Optional extras:**

```bash
pip install -e ".[dashboard]"    # CLI dashboard (python -m dashboard)
pip install -e ".[engineering]"  # Routing, inverse design, HEaC (Qiskit, PyTorch)
pip install -e ".[test]"         # Pytest and test deps
pip install -e ".[all]"          # All optional dependencies
```

Entry points: `qasic-dashboard`, `qasic-pulse` (pulse compile CLI). Build artifacts: `pip install build && python -m build`.

---

## Orchestration and deployment (four concepts)

| Concept | What it is | Where |
|--------|------------|--------|
| **Engineering pipeline (EaC)** | Metasurface DAG: routing → inverse design → HEaC → GDS → DRC/LVS (and optional thermal, parasitic, calibration). Run via `python src/core_compute/engineering/run_pipeline.py` or `--use-orchestrator` for [Prefect](src/backend/). | [docs/app/ORCHESTRATION.md](docs/app/ORCHESTRATION.md) |
| **Workflows** | User-defined DAGs in the app: task types with per-node backend (Local, IBM QPU, EKS). Executed by the **Hybrid Compute Dispatcher** in the backend. | Workflows page, [src/backend/README.md](src/backend/README.md) |
| **Deploy** | Where the stack runs: Local (Docker Compose), VM, or cloud (AWS, GCP, Azure, OpenNebula). Deploy page in the app or [platform/deploy/README.md](platform/deploy/README.md). | [platform/deploy/](platform/deploy/) |
| **IaC Orchestrator** | Advanced infra DAG: Tofu init → plan → approval → apply, custom scripts. For power users. | [platform/iac-orchestrator/README.md](platform/iac-orchestrator/README.md) |

---

## Project layout

```
qasic-engineering-as-code/
├── README.md
├── pyproject.toml
├── config/                    # App and pipeline config (e.g. app_config.yaml)
├── src/
│   ├── frontend/             # Vite + React SPA (Workflows, Deploy, Run Pipeline, etc.)
│   ├── backend/              # FastAPI, Celery, executor, dispatcher, task_registry, pipeline_flow
│   └── core_compute/         # Engineering, ASIC, protocols, pulse, state (simulation & pipelines)
├── platform/
│   ├── deploy/               # Docker Compose, Helm chart, Deploy UI commands
│   ├── infra/                # OpenTofu (AWS; GCP/Azure/OpenNebula stubs)
│   └── iac-orchestrator/     # IaC DAG UI → OpenTofu (backend only)
├── docs/
│   ├── README.md             # Doc index → app/ and research/
│   ├── app/                  # Application docs (APIs, orchestration, HEaC, QUANTUM_ASIC, etc.)
│   └── research/             # Whitepapers, LaTeX sources, build_pdfs.ps1
├── demos/                    # demo_teleport, demo_thief, demo_commitment, demo_asic, etc.
├── apps/                     # BQTC, qrnc (applications using pipeline / QRNG)
├── dashboard/                # CLI dashboard (python -m dashboard)
├── storage/                  # Persistence (DB, MLflow)
├── tests/                    # Pytest suite
└── QRNG.PY                   # Shared quantum RNG (e.g. apps/qrnc)
```

Full-stack diagram: [docs/app/architecture_overview.md](docs/app/architecture_overview.md).

---

## Quantum ASIC and protocols

| Protocol | What it demonstrates |
|----------|----------------------|
| **Entanglement & teleportation** | Bell pair creation, state transfer with classical message, no cloning. |
| **Tamper-evidence (Thief)** | Intercepting the "message" disturbs the state; receiver sees fidelity drop. |
| **Toy bit commitment** | Commit to a bit using shared entanglement + classical reveal (toy assumptions). |
| **3-qubit bit-flip code** | Minimal QEC on the ASIC linear chain. |
| **QKD (BB84 / E91)** | Pedagogical prepare-and-measure and entanglement-based key distribution. |

**Quantum ASIC spec:** 3 qubits, linear chain `0 — 1 — 2`; gates H, X, Z, CNOT. See [docs/app/QUANTUM_ASIC.md](docs/app/QUANTUM_ASIC.md) and `python demos/demo_asic.py`. For topologies (star, repeater): `src/core_compute/asic/topology_builder` and [docs/app/TOPOLOGY_BUILDER.md](docs/app/TOPOLOGY_BUILDER.md).

**More demos:** `python demos/demo_noise.py`, `demo_bitflip_code.py`, `demo_bb84.py`, `demo_e91.py`. **Security (toy):** No unconditional security; see [docs/app/CHANNEL_NOISE.md](docs/app/CHANNEL_NOISE.md) and [docs/app/CV_QUANTUM_RADAR.md](docs/app/CV_QUANTUM_RADAR.md).

---

## Engineering pipeline

Run the metasurface pipeline (routing → inverse design → optional HEaC → GDS → DRC/LVS):

```bash
python src/core_compute/engineering/run_pipeline.py -o pipeline_result
# Tape-out flags: --heac --gds --drc --lvs --thermal --parasitic
# With Prefect: --use-orchestrator
```

See [src/core_compute/engineering/README.md](src/core_compute/engineering/README.md) for IBM Quantum and options. HEaC, thermal, parasitics, calibration: [docs/app/HEaC_opensource_Meep.md](docs/app/HEaC_opensource_Meep.md), [docs/app/THERMAL_AND_PARASITICS.md](docs/app/THERMAL_AND_PARASITICS.md), [docs/app/CALIBRATION_DIGITAL_TWIN.md](docs/app/CALIBRATION_DIGITAL_TWIN.md).

---

## Applications

**BQTC** (Bayesian-Quantum Traffic Controller) and **qrnc** (quantum-backed tokens, BitCommit-style exchange) live under [apps/](apps/); they use the shared **QRNG.PY** at repo root. See [apps/README.md](apps/README.md) and [docs/app/APPLICATIONS.md](docs/app/APPLICATIONS.md).

**Pulse control:** `src/core_compute/pulse/` compiles ASIC gate circuits to pulse schedules. Run `qasic-pulse --circuit teleport -o schedule.json`; see [docs/app/PULSE_CONTROL.md](docs/app/PULSE_CONTROL.md).

---

## Testing

From repo root:

```bash
pip install -e ".[test]"
python -m pytest tests/ -v
```

Optional: install `.[engineering]` for routing and inverse-design tests. Hardware CI (`.github/workflows/hardware-ci.yml`) runs tests, pipeline validation, Trivy container scan, and optional ECR push; see [platform/deploy/README.md](platform/deploy/README.md). Store baselines in `src/core_compute/engineering/ci_baseline/` for GDS/manifest diff.

---

## Document guide

| If you want… | Read… |
|--------------|--------|
| **Vision, protocols, roadmap** | [docs/research/WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.md](docs/research/WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.md) |
| **Infrastructure-aware architecture (IAA)** | [docs/research/Whitepaper_Infrastructure_Aware_Application.md](docs/research/Whitepaper_Infrastructure_Aware_Application.md) |
| **Full document index** | [docs/app/README.md](docs/app/README.md) |
| **Pulse control** | [docs/app/PULSE_CONTROL.md](docs/app/PULSE_CONTROL.md) |
| **HEaC, DRC/LVS** | [docs/app/HEaC_opensource_Meep.md](docs/app/HEaC_opensource_Meep.md) |
| **Thermal, parasitics** | [docs/app/THERMAL_AND_PARASITICS.md](docs/app/THERMAL_AND_PARASITICS.md) |
| **Calibration** | [docs/app/CALIBRATION_DIGITAL_TWIN.md](docs/app/CALIBRATION_DIGITAL_TWIN.md) |
| **Channel noise** | [docs/app/CHANNEL_NOISE.md](docs/app/CHANNEL_NOISE.md) |
| **Toy protocol descriptions** | [PROTOCOLS.md](PROTOCOLS.md) |
| **LaTeX PDFs** | From repo root: `.\docs\research\build_pdfs.ps1` — see [docs/app/README.md](docs/app/README.md#building-pdfs-tex-live) |

---

## References

- [Quirk: Quantum Circuit Simulator](https://algassert.com/quirk) — e.g. teleportation + "Thief" circuit.
- Mayers–Lo–Chau: no-go for unconditional quantum bit commitment.
- Micius satellite: space-based entanglement distribution and teleportation.
