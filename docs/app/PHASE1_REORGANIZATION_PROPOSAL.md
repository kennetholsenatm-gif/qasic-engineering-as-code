# Phase 1: Logical Repository Reorganization — Proposal

**Repository:** qasic-engineering-as-code  
**Goal:** Centralize structure around the QASIC Engineering-as-Code (HEaC) application with a clear `/src` (application) and `/platform` (deployment/infra) layout.

---

## 1. Proposed new folder tree

```
qasic-engineering-as-code/
├── src/                          # Application core (new)
│   ├── frontend/                 # FBP WUI — consolidated from frontend/ + tools/iac-orchestrator/frontend/
│   │   ├── src/
│   │   │   ├── components/        # PipelineDag.jsx, TaskNode.jsx, StageNode (merged), Layout, etc.
│   │   │   ├── pages/
│   │   │   ├── App.jsx, main.jsx, index.css
│   │   │   └── ...
│   │   ├── index.html, package.json, vite.config.js, nginx.conf, tailwind.config.js, postcss.config.js
│   │   └── README.md
│   ├── backend/                  # FastAPI + Celery + DAG orchestration (merged app/ + orchestration/)
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI app entry (from app/main.py)
│   │   ├── celery_app.py
│   │   ├── tasks.py
│   │   ├── job_store.py
│   │   ├── executor.py           # from orchestration/executor.py
│   │   ├── pipeline_flow.py
│   │   ├── pipeline_tasks.py
│   │   ├── pipeline_params.py
│   │   ├── task_registry.py
│   │   ├── dag_validate.py
│   │   ├── calibration_flow.py
│   │   ├── requirements.txt
│   │   └── README.md
│   └── core_compute/             # Domain logic used by backend (engineering, asic, protocols, pulse, state)
│       ├── engineering/          # moved from root engineering/
│       ├── asic/                  # moved from root asic/
│       ├── protocols/            # moved from root protocols/
│       ├── pulse/                # moved from root pulse/
│       └── state/                # moved from root state/
│
├── platform/                     # Deployment & infrastructure (new)
│   ├── deploy/                   # Helm charts, K8s (moved from deploy/)
│   │   └── helm/qasic/           # Chart + templates + values
│   ├── infra/                    # OpenTofu, Grafana (moved from infra/)
│   │   ├── tofu/
│   │   └── grafana/
│   └── iac-orchestrator/         # Optional IaC DAG tool (from tools/iac-orchestrator, frontend removed)
│       ├── backend/
│       ├── docker-compose.yml
│       ├── Dockerfile.backend
│       └── README.md
│
├── docs/
│   ├── research/                 # Whitepapers, LaTeX, build artifacts (new)
│   │   ├── *.tex, *.aux, *.log, *.out
│   │   ├── Whitepaper_*.md, Cryogenic_*.md, Engineering_as_Code_*.md, etc.
│   │   ├── quantum-terrestrial-backhaul.md, quantum-terrestrial-backhaul.tex
│   │   └── build_pdfs.ps1
│   └── app/                      # Application-focused docs (new)
│       ├── README.md             # Doc index (from docs/README.md, updated)
│       ├── architecture_overview.md
│       ├── ORCHESTRATION.md
│       ├── DATA_PERSISTENCE.md, UNIFIED_UX.md
│       ├── PULSE_CONTROL.md, HEaC_opensource_Meep.md, THERMAL_AND_PARASITICS.md
│       ├── CALIBRATION_DIGITAL_TWIN.md, CHANNEL_NOISE.md
│       ├── QUANTUM_ASIC.md, TOPOLOGY_BUILDER.md, QKD.md, CV_QUANTUM_RADAR.md
│       ├── APPLICATIONS.md, DATA_AND_CONTROL_PLANE_QUANTUM_ASIC.md, THEORETICAL_APPLICATIONS.md
│       ├── NEXT_STEPS_ROADMAP.md, ROADMAP_STATUS.md
│       └── superscreen_integration.md
│
├── config/                       # Unchanged (backend references from root or src/backend)
├── storage/                      # Unchanged
├── dashboard/                    # CLI dashboard — unchanged
├── demos/                        # Demo scripts — unchanged
├── tests/                        # Pytest — unchanged (paths updated to src/backend, src/core_compute)
├── apps/                         # BQTC, qrnc — unchanged (consume pipeline; optional move later)
│
├── Dockerfile.api                # Root (build context: repo root; COPY paths updated to src/)
├── Dockerfile.frontend           # Root (COPY src/frontend)
├── Dockerfile.jupyter            # Root (unchanged or COPY paths if it references app/engineering)
├── docker-compose.yml            # Root (build context + paths updated)
├── docker-compose.full.yml
├── pyproject.toml                # Root (package dirs updated)
├── MANIFEST.in
├── Makefile                      # Root (targets updated for src/ and platform/)
├── cli.py                        # Root (imports updated)
├── requirements.txt              # Root
├── requirements-test.txt
├── requirements-dashboard.txt
├── .env.example, .gitignore, .dockerignore, .gitattributes
├── PROTOCOLS.md                  # Root
├── README.md                     # Root (rewritten in Phase 4)
└── ... (other root files: QRNG.PY, star_routing.json, etc.)
```

**Summary of new top-level layout:**

| Path        | Purpose                                                                 |
|------------|-------------------------------------------------------------------------|
| `src/`     | All application code: frontend (FBP WUI), backend (API + DAG), core_compute (domain). |
| `platform/`| All deployment and infra: Helm, OpenTofu, optional IaC orchestrator.   |
| `docs/research/` | LaTeX sources, whitepapers, PDF build script and artifacts.        |
| `docs/app/`     | Application and product documentation.                             |

---

## 2. Exact file and directory moves

### 2.1 Create `src/` and move frontend

| Action | Source | Destination |
|--------|--------|-------------|
| Move   | `frontend/` (entire directory) | `src/frontend/` |
| Merge  | `tools/iac-orchestrator/frontend/src/components/StageNode.jsx` | `src/frontend/src/components/StageNode.jsx` (add; keep PipelineDag, TaskNode) |
| Merge  | `tools/iac-orchestrator/frontend/src/pages/Pipelines.jsx` | `src/frontend/src/pages/` (integrate into FBP flow or keep as optional page) |
| Merge  | Any iac-orchestrator frontend styles/config (e.g. index.css, vite tailwind) | Merge into `src/frontend/` where missing or differing |

**Note:** The primary FBP canvas remains `PipelineDag.jsx` and `TaskNode.jsx` (already using React Flow). StageNode and Pipelines page are merged so the single WUI can offer both pipeline views if desired.

### 2.2 Create `src/backend/` (merge `app/` + `orchestration/`)

| Action | Source | Destination |
|--------|--------|-------------|
| Move   | `app/__init__.py` | `src/backend/__init__.py` |
| Move   | `app/main.py` | `src/backend/main.py` |
| Move   | `app/celery_app.py` | `src/backend/celery_app.py` |
| Move   | `app/tasks.py` | `src/backend/tasks.py` |
| Move   | `app/job_store.py` | `src/backend/job_store.py` |
| Move   | `app/requirements.txt` | `src/backend/requirements.txt` |
| Move   | `app/README.md` | `src/backend/README.md` |
| Move   | `orchestration/__init__.py` | (merge into `src/backend/` or keep one `__init__.py`) |
| Move   | `orchestration/executor.py` | `src/backend/executor.py` |
| Move   | `orchestration/pipeline_flow.py` | `src/backend/pipeline_flow.py` |
| Move   | `orchestration/pipeline_tasks.py` | `src/backend/pipeline_tasks.py` |
| Move   | `orchestration/pipeline_params.py` | `src/backend/pipeline_params.py` |
| Move   | `orchestration/task_registry.py` | `src/backend/task_registry.py` |
| Move   | `orchestration/dag_validate.py` | `src/backend/dag_validate.py` |
| Move   | `orchestration/calibration_flow.py` | `src/backend/calibration_flow.py` |
| Move   | `orchestration/README.md` | (merge into `src/backend/README.md` or discard) |

**Deletions after move:** Remove now-empty directories `app/` and `orchestration/`.

### 2.3 Create `src/core_compute/` (domain modules)

| Action | Source | Destination |
|--------|--------|-------------|
| Move   | `engineering/` (entire tree) | `src/core_compute/engineering/` |
| Move   | `asic/` (entire tree) | `src/core_compute/asic/` |
| Move   | `protocols/` (entire tree) | `src/core_compute/protocols/` |
| Move   | `pulse/` (entire tree) | `src/core_compute/pulse/` |
| Move   | `state/` (entire tree) | `src/core_compute/state/` |

**Deletions after move:** Remove now-empty root-level `engineering/`, `asic/`, `protocols/`, `pulse/`, `state/`.

### 2.4 Create `platform/` (deploy + infra + iac-orchestrator)

| Action | Source | Destination |
|--------|--------|-------------|
| Move   | `deploy/` (entire tree) | `platform/deploy/` |
| Move   | `infra/` (entire tree) | `platform/infra/` |
| Move   | `tools/iac-orchestrator/` (entire tree) | `platform/iac-orchestrator/` |
| Delete | `tools/iac-orchestrator/frontend/` | (already merged into `src/frontend/` before move; or move then delete frontend from platform/iac-orchestrator) |

**Recommended:** Move `tools/iac-orchestrator` → `platform/iac-orchestrator` and then delete `platform/iac-orchestrator/frontend/` so the platform tool is backend-only (main WUI is in `src/frontend`).

**Deletions after move:** Remove empty `tools/` if nothing else remains.

### 2.5 Create `docs/research/` and `docs/app/`

**Move to `docs/research/`** (LaTeX, whitepapers, build):

- All `docs/*.tex` (8 files)
- All `docs/*.aux` (6 files)
- All `docs/*.log` (6 files)
- All `docs/*.out` (present in docs; move all)
- Whitepaper / long-form `.md` that are research-oriented:
  - `WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.md`
  - `Cryogenic_Metamaterial_Architectures_Quantum_SATCOM.md`
  - `Computational_Materials_Science_Cryogenic_Quantum_Metamaterials.md`
  - `Engineering_as_Code_Distributed_Computational_Roadmap.md`
  - `Whitepaper_Unified_Quantum_Metasurfaces_SATCOM.md`
  - `quantum-terrestrial-backhaul.md`
- `docs/build_pdfs.ps1` → `docs/research/build_pdfs.ps1`

**Move to `docs/app/`** (application docs):

- `docs/README.md` → `docs/app/README.md` (doc index; update links to research/ and app/)
- `docs/architecture_overview.md`
- `docs/ORCHESTRATION.md`, `docs/DATA_PERSISTENCE.md`, `docs/UNIFIED_UX.md`
- `docs/PULSE_CONTROL.md`, `docs/HEaC_opensource_Meep.md`, `docs/THERMAL_AND_PARASITICS.md`
- `docs/CALIBRATION_DIGITAL_TWIN.md`, `docs/CHANNEL_NOISE.md`
- `docs/QUANTUM_ASIC.md`, `docs/TOPOLOGY_BUILDER.md`, `docs/QKD.md`, `docs/CV_QUANTUM_RADAR.md`
- `docs/APPLICATIONS.md`, `docs/DATA_AND_CONTROL_PLANE_QUANTUM_ASIC.md`, `docs/THEORETICAL_APPLICATIONS.md`
- `docs/NEXT_STEPS_ROADMAP.md`, `docs/ROADMAP_STATUS.md`
- `docs/superscreen_integration.md`

**Deletions:** After moving files into `docs/research/` and `docs/app/`, the only remaining content in `docs/` should be the two subdirectories (and optionally a minimal `docs/README.md` that points to `app/` and `research/`). No orphaned files in `docs/`.

---

## 3. Post-move code and config updates (required for Phase 1 to be runnable)

### 3.1 Python imports and entry points

- **Backend entry:** Change from `uvicorn app.main:app` to `uvicorn src.backend.main:app` (or keep a root `app` package that re-exports `src.backend.main` for minimal change).
- **PYTHONPATH:** Set to repo root so that `src.backend` and `src.core_compute` are importable; backend code should import e.g. `from src.core_compute.engineering...` or add `src` to `sys.path` and use `core_compute.engineering`.
- **Celery:** Update `celery_app.py` and any `app.tasks` references to `src.backend.tasks` (or keep `app` as a namespace package pointing at `src.backend`).
- **Internal imports in backend:** Replace `from app.` with `from src.backend.` and `import engineering`, `asic`, `protocols`, etc. with `from src.core_compute import engineering, asic, protocols, ...` (or equivalent).
- **pyproject.toml:** Update package dirs and entry points (e.g. `qasic-dashboard`, `qasic-pulse`) to reference new locations if they point at `app` or `orchestration`.

### 3.2 Docker

- **Dockerfile.api:**  
  - `COPY app/ app/` → `COPY src/ src/` (and `COPY config/ config/`, `COPY storage/ storage/` if still at root).  
  - `CMD ["uvicorn", "app.main:app", ...]` → `CMD ["uvicorn", "src.backend.main:app", ...]` (or keep `app.main` if you add a root shim).  
  - Add `COPY requirements.txt` and backend requirements; install from root + `src/backend/requirements.txt` as today.
- **Dockerfile.frontend:**  
  - `COPY frontend/ ./` → `COPY src/frontend/ ./`  
  - `COPY frontend/nginx.conf` → `COPY src/frontend/nginx.conf`
- **docker-compose.yml / docker-compose.full.yml:**  
  - Build context remains repo root.  
  - `dockerfile: Dockerfile.api` and `dockerfile: Dockerfile.frontend` unchanged.  
  - Any volumes or paths that referenced `app/` or `frontend/` should reference `src/backend/` and `src/frontend/`.

### 3.3 Helm / platform

- **Build instructions:** In `platform/deploy/README.md` and `platform/deploy/helm/qasic/README.md`, document that the API image is built from repo root with `docker build -f Dockerfile.api .` and frontend with `docker build -f Dockerfile.frontend .` (no path changes to Dockerfile locations; only COPY paths inside Dockerfiles change).
- **Chart values:** No change to image names (`qasic-api`, `qasic-frontend`); they still reference the same image names/tags.

### 3.4 Tests and tooling

- **pytest:** Update `tests/` imports and any path references from `app`, `orchestration`, `engineering`, `asic`, `protocols`, `pulse`, `state` to `src.backend` and `src.core_compute.*`.
- **dashboard:** If it imports `app` or orchestration, update to `src.backend` (or keep `app` as shim).
- **cli.py:** Update imports to use `src.backend` / `src.core_compute` as needed.
- **engineering/run_pipeline.py:** Now under `src/core_compute/engineering/`; any scripts that invoke it (e.g. `python engineering/run_pipeline.py`) become `python -m src.core_compute.engineering.run_pipeline` or `python src/core_compute/engineering/run_pipeline.py` from repo root.

### 3.5 Documentation links

- **docs/app/README.md:** Update all links to point to `../research/` for LaTeX/whitepapers and to sibling files in `docs/app/`.
- **Root README.md:** In Phase 4 you will rewrite it; for Phase 1, update any paths (e.g. `docs/...` → `docs/app/...` or `docs/research/...`).
- **build_pdfs.ps1:** Update paths inside the script so LaTeX files are in `docs/research/` and output (if any) goes to a defined location.

---

## 4. Summary table: moves and deletions

| Category | Moves | Deletions |
|----------|-------|-----------|
| Frontend | `frontend/` → `src/frontend/`; merge iac-orchestrator frontend into `src/frontend` | — |
| Backend  | `app/*` + `orchestration/*` → `src/backend/*` | `app/`, `orchestration/` (after move) |
| Core compute | `engineering/`, `asic/`, `protocols/`, `pulse/`, `state/` → `src/core_compute/<name>/` | Original five dirs (after move) |
| Platform | `deploy/` → `platform/deploy/`; `infra/` → `platform/infra/`; `tools/iac-orchestrator/` → `platform/iac-orchestrator/` | `platform/iac-orchestrator/frontend/` (after merge); `tools/` if empty |
| Docs     | 8 .tex, 6 .aux, 6 .log, .out, 6 whitepaper .md, build_pdfs.ps1 → `docs/research/`; ~18 .md → `docs/app/` | Orphaned files in `docs/` (none left) |

---

## 5. What stays at repo root (unchanged or path-only updates)

- **Root:** `Dockerfile.api`, `Dockerfile.frontend`, `Dockerfile.jupyter`, `docker-compose.yml`, `docker-compose.full.yml`, `pyproject.toml`, `MANIFEST.in`, `Makefile`, `cli.py`, `requirements.txt`, `requirements-test.txt`, `requirements-dashboard.txt`, `.env.example`, `.gitignore`, `.dockerignore`, `.gitattributes`, `PROTOCOLS.md`, `README.md`, `QRNG.PY`, `star_routing.json`, etc.
- **Unmoved dirs:** `config/`, `storage/`, `dashboard/`, `demos/`, `tests/`, `apps/`, `.devcontainer/`, `.github/`, `.vscode/`.

---

Once you approve this proposal, the next step is to perform the moves and apply the code/config updates above so that the stack builds, tests pass, and the app runs locally and via Helm as before.
