# QASIC Engineering-as-Code

**Repository:** [github.com/kennetholsenatm-gif/qasic-engineering-as-code](https://github.com/kennetholsenatm-gif/qasic-engineering-as-code)

**Quantum ASIC and Engineering-as-Code (EaC) pipeline:** protocols, routing, inverse design, quantum illumination, and CV quantum radar. Pedagogical implementations of **quantum teleportation**, **tamper-evident channels**, and **bit commitment** over a quantum link, plus DV/CV quantum illumination—in pure Python with NumPy.

**Status:** The full stack (protocols, routing, inverse design) runs **without physical metamaterials**: simulation and real IBM Quantum for routing, CPU/GPU for inverse design. The repo also includes **tape-out–oriented** features: PDK-aware GDS with DRC/LVS, pulse-level control synthesis (OpenPulse/pseudo), cryogenic thermal and parasitic extraction, Hardware CI, and digital-twin calibration. See [Whitepaper §8 and §10](docs/WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.md) for vision and supporting code.

---

## Installation and quick start

Run from the **repo root** (use `py` or `python` as on your system; on Windows you may need `py` if `python` is not on PATH):

```bash
git clone https://github.com/kennetholsenatm-gif/qasic-engineering-as-code.git
cd qasic-engineering-as-code
pip install -r requirements.txt
python demos/demo_teleport.py
python demos/demo_thief.py
python demos/demo_commitment.py
python demos/demo_asic.py
```

Demos are script-style (no CLI arguments). For the full **engineering pipeline** (routing then inverse design), run `python engineering/run_pipeline.py`; it writes `engineering/<base>_routing.json`, `engineering/<base>_inverse.json`, and `engineering/<base>_inverse_phases.npy` (default base: `pipeline_result`). Use `--heac --gds --drc --lvs` for tape-out–oriented runs; see [Engineering pipeline](#engineering-pipeline) below.

### Optional extras and packaging

The project is installable as a Python package for use in scripts, CI, or as the basis for an installer:

```bash
# From repo root: install in editable mode (development)
pip install -e .

# Optional extras
pip install -e ".[dashboard]"           # CLI dashboard (python -m dashboard)
pip install -e ".[app]"                  # FastAPI + Celery (for uvicorn app.main:app)
pip install -e ".[engineering]"         # Routing, inverse design, HEaC (Qiskit, PyTorch)
pip install -e ".[test]"                # Pytest and test deps
pip install -e ".[all]"                 # All optional dependencies
```

To build distributable artifacts: `pip install build && python -m build`. This produces `dist/*.whl` and sdist. Entry points: `qasic-dashboard` (CLI dashboard), `qasic-pulse` (pulse compile CLI). For public distribution, add a `LICENSE` file at repo root and optionally reference it in `MANIFEST.in`.

---

## Orchestration and deployment

Four concepts keep **where the app runs** separate from **what it runs**:

1. **Engineering pipeline (EaC)** — The metasurface DAG: routing → inverse design → HEaC → GDS → DRC/LVS (and optional thermal, parasitic, calibration). Run via `python engineering/run_pipeline.py` (sequential) or `--use-orchestrator` for [Prefect](orchestration/) (retries, optional server). See [docs/ORCHESTRATION.md](docs/ORCHESTRATION.md).
2. **Workflows** — User-defined DAGs in the web app: task types (protocols, routing, inverse design, etc.) with per-node backend (Local, IBM QPU, EKS). Execution is via the app’s [orchestration executor](orchestration/executor.py).
3. **Deploy** — Where the QASIC stack runs: Local (Docker Compose), VM, or cloud-native (AWS, GCP, Azure, OpenNebula). Use the **Deploy** page in the web app for a target-centric UI (or “Generate commands” to run Tofu/Helm yourself). See [deploy/README.md](deploy/README.md).
4. **IaC Orchestrator** — Advanced infra DAG in [tools/iac-orchestrator](tools/iac-orchestrator): visual pipeline (Tofu init → plan → approval → apply, custom scripts). For power users who want full control; linked from the Deploy page.

---

## Running the stack (local)

### Docker

If you see an error that `.env` is not found, create it from the template: `copy .env.example .env` (Windows) or `cp .env.example .env` (Mac/Linux).

**Core stack** (API, frontend, Celery, Redis, Postgres)—production parity in one command:

```bash
docker compose up -d --build
# Or: make run-local-core
```

Then open the frontend at `http://localhost` (or port 80). For Jupyter: `docker compose --profile jupyter run --service-ports jupyter`.

**Full stack** (core + InfluxDB, MLflow, Grafana):

```bash
make run-local
make down-local
# Or: docker compose -f docker-compose.full.yml up -d --build
```

Then open: frontend **http://localhost**, API **http://localhost:8000/docs**, MLflow **http://localhost:5000**, Grafana **http://localhost:3000**. To provision **AWS** (RDS, ElastiCache, EKS): `cd infra/tofu && tofu init && tofu apply -var="deployment_target=aws"`. See [infra/tofu/README.md](infra/tofu/README.md).

### Cursor + Docker

Use [Cursor](https://cursor.com) with Docker Desktop for one-click Compose and optional Dev Containers. **Prerequisites:** Docker Desktop installed and running (Windows: WSL2 backend recommended). Install the **Docker** and **Dev Containers** extensions in Cursor.

- **Quick run:** Open this repo in Cursor, then **Terminal → Run Task…** and choose **Docker: Compose up (core)** or **Docker: Compose up (full stack)**.
- **Stop:** Run task **Docker: Compose down**.
- **Dev Container:** **Command Palette → Dev Containers: Reopen in Container** to open the project inside the API container.

Compose files: [docker-compose.yml](docker-compose.yml) (core), [docker-compose.full.yml](docker-compose.full.yml) (full stack). **IaC DAG tool:** [tools/iac-orchestrator/](tools/iac-orchestrator/) — `docker compose -f tools/iac-orchestrator/docker-compose.yml up -d --build`, then http://localhost:8080.

### CLI dashboard

A terminal menu to run protocols, routing, pipeline, and inverse design and view last results without the web app:

```bash
pip install -r requirements-dashboard.txt
python -m dashboard
```

Or `python dashboard/cli_dashboard.py` from the repo root. See [dashboard/](dashboard/).

### Web app

Browser UI: FastAPI backend + React SPA. From repo root: `pip install -r app/requirements.txt`, then `uvicorn app.main:app --reload`, then `cd frontend && npm install && npm run dev`. See [app/README.md](app/README.md) and [frontend/README.md](frontend/README.md).

- **Phase viewer (3D):** View the latest inverse-design phase profile (run pipeline or inverse design first).
- **Async IBM jobs:** Protocol runs on IBM hardware return a `job_id`; the UI shows live status via WebSocket.

---

## Quantum ASIC and protocols

### Concepts

| Protocol | What it demonstrates |
|----------|----------------------|
| **Entanglement & teleportation** | Bell pair creation, state transfer with classical message, no cloning. |
| **Tamper-evidence (Thief)** | Intercepting the "message" disturbs the state; receiver sees fidelity drop. |
| **Toy bit commitment** | Commit to a bit using shared entanglement + classical reveal; security relies on tamper-evident channel + bounded storage (toy assumptions). |
| **3-qubit bit-flip code** | Minimal QEC: encode one logical qubit, correct one bit-flip error on the ASIC linear chain. |
| **QKD (BB84 / E91)** | Pedagogical prepare-and-measure (BB84) and entanglement-based (E91) key distribution. |

### Security assumptions (toy)

- **No unconditional security.** The bit-commitment toy is *not* information-theoretically secure (Mayers–Lo–Chau no-go applies in the full model). We assume a **passive** adversary or **bounded quantum storage** so the protocol is binding/hiding in a pedagogical setting.
- **Perfect devices.** No channel loss, no detector noise—we're illustrating principles. For noisy links, use the **channel noise simulator** or **DV quantum illumination** (thermal loss channel). For physics-accurate microwave-style TMSV and thermal baths, use the **toy CV quantum radar** (covariance matrices); see [docs/CV_QUANTUM_RADAR.md](docs/CV_QUANTUM_RADAR.md).

### Quantum ASIC spec

The **Quantum ASIC** idea: reduce hardware to **only the gates and topology** needed for these protocols—no full connectivity, no universal gate set.

- **3 qubits**, linear chain: `0 — 1 — 2` (only adjacent pairs can do CNOT).
- **Gates:** H, X, Z, CNOT (and optional Rx for the tamper model).

All three protocols compile to this minimal set and validate against it. See **[docs/QUANTUM_ASIC.md](docs/QUANTUM_ASIC.md)** for the spec and **`python demos/demo_asic.py`** to validate and run. For routing and visualization of other topologies (star, repeater chain), see **`asic/topology_builder`** and **[docs/TOPOLOGY_BUILDER.md](docs/TOPOLOGY_BUILDER.md)**.

### More demos

```bash
python demos/demo_noise.py         # Channel noise (depolarizing, amplitude/phase damping)
python demos/demo_bitflip_code.py  # 3-qubit bit-flip repetition code (QEC)
python demos/demo_bb84.py          # BB84 QKD (pedagogical)
python demos/demo_e91.py           # E91 QKD (Bell pairs + CHSH)
```

**Channel noise:** `state/channels.py` (Kraus channels); `protocols/noise.py` (`NoiseModel`, `run_teleport_with_noise`, `run_thief_with_noise`). See [docs/CHANNEL_NOISE.md](docs/CHANNEL_NOISE.md).

---

## Engineering pipeline

The **EaC pipeline** runs: routing (QUBO/QAOA: logical qubits → physical nodes) → inverse design (topology → phase profile) → optional HEaC (phases → geometry manifest → GDS) → DRC/LVS, thermal, parasitic, calibration.

- **Run:** `python engineering/run_pipeline.py` (sequential) or `--use-orchestrator` for Prefect. Use `--routing-method rl` for RL-based routing or `--model gnn` for GNN inverse design; `--with-superscreen` for inductance from routing topology.
- **Tape-out flags:** `--heac`, `--gds`, `--drc`, `--lvs`, `--thermal`, `--parasitic`.
- **IBM Quantum:** For affordable runs (under 5 minutes QPU time), see [Engineering as Code on IBM Quantum](engineering/README.md#engineering-as-code-on-ibm-quantum-affordable-5-min) in the engineering README.

### Tape-out and production features

- **HEaC + PDK:** Geometry manifest → GDS with optional [PDK config](engineering/heac/pdk_config.yaml); [DRC](engineering/heac/run_drc_klayout.py) and [LVS](engineering/heac/run_lvs_klayout.py) (KLayout or mock). See [docs/HEaC_opensource_Meep.md](docs/HEaC_opensource_Meep.md).
- **Thermal & parasitics:** [Thermal stage report](engineering/thermal_stages.py) (routing + phases → 10 mK / 4 K / 50 K); [parasitic extraction](engineering/parasitic_extraction.py) (manifest → layout-aware decoherence). See [docs/THERMAL_AND_PARASITICS.md](docs/THERMAL_AND_PARASITICS.md).
- **Digital twin calibration:** [engineering/calibration/](engineering/calibration/) ingests quantum telemetry (T1/T2 per qubit), runs a Bayesian update, and writes `decoherence_from_calibration.json` for routing/simulation. See [docs/CALIBRATION_DIGITAL_TWIN.md](docs/CALIBRATION_DIGITAL_TWIN.md).
- **Hardware CI:** On push/PR, GitHub Actions runs tests, pipeline + thermodynamic validation, and optional manifest diff; see [Hardware CI](#hardware-ci) below.

---

## Applications

Two applications live under **`apps/`** and use the shared **`QRNG.PY`** at repo root where needed:

- **[BQTC](apps/README.md#bqtc-bayesian-quantum-traffic-controller)** — Bayesian-Quantum Traffic Controller: Telemetry → Bayesian inference → Qiskit QUBO path selection → VyOS BGP actuator.
- **[qrnc](apps/README.md#qrnc-quantum-backed-tokens-and-exchange)** — Quantum-backed tokens and BitCommit-style two-party exchange.

See [apps/README.md](apps/README.md) for run instructions and [docs/APPLICATIONS.md](docs/APPLICATIONS.md) for purpose and security caveats.

### Pulse control

**`pulse/`** compiles ASIC gate circuits to pulse schedules (Qiskit OpenPulse or a pseudo-schedule dict) for microwave/optical control. Run `python -m pulse --circuit teleport -o schedule.json` from the repo root; see [docs/PULSE_CONTROL.md](docs/PULSE_CONTROL.md).

### Theoretical applications

Conceptual extensions to **data and control plane** (tamper-evident tunneling, FEC, key streaming, BGP commitment, SD-WAN QAOA, OAM fault localization) are described in [docs/DATA_AND_CONTROL_PLANE_QUANTUM_ASIC.md](docs/DATA_AND_CONTROL_PLANE_QUANTUM_ASIC.md). Summary and mapping to code: [docs/THEORETICAL_APPLICATIONS.md](docs/THEORETICAL_APPLICATIONS.md).

---

## Project layout

```
qasic-engineering-as-code/
├── README.md
├── requirements.txt
├── QRNG.PY                    # Shared quantum RNG (used by apps/qrnc)
├── apps/                      # Applications: BQTC, qrnc
├── docs/                      # Document index, QUANTUM_ASIC, whitepapers, HEaC, etc.
├── state/                     # Minimal qubit simulation + toy CV (Gaussian)
├── asic/                      # Quantum ASIC: minimal gates + topology
├── pulse/                     # Gate → pulse schedule (OpenPulse / pseudo)
├── protocols/                 # Teleportation, tamper-evident, commitment, QKD, bit-flip, noise, QI, radar
├── engineering/               # Routing, inverse design, HEaC, thermal/parasitics, calibration
├── dashboard/                 # CLI dashboard (python -m dashboard)
├── app/                       # FastAPI backend (uvicorn app.main:app)
├── frontend/                  # Vite + React SPA
├── config/                    # App and pipeline config
├── deploy/                    # Kubernetes/Helm chart (see deploy/README.md)
├── tools/iac-orchestrator/    # IaC DAG UI → OpenTofu
├── infra/tofu/                # OpenTofu (AWS; gcp/azure/opennebula stubs)
├── orchestration/             # Prefect 2 DAG (pipeline, calibration)
├── storage/                   # Persistence (DB, MLflow)
├── tests/                     # Pytest suite
└── demos/                     # demo_teleport, demo_thief, demo_commitment, demo_asic, etc.
```

Full tree with file-level detail is in the [repository](https://github.com/kennetholsenatm-gif/qasic-engineering-as-code); see also [docs/architecture_overview.md](docs/architecture_overview.md).

---

## Testing

From the repo root:

```bash
pip install -r requirements-test.txt
python -m pytest tests/ -v
```

Optional: install `engineering/requirements-engineering.txt` to run routing and inverse-net tests (including `test_engineering_routing.py` QUBO build when `qiskit-optimization` is available). The suite also includes `test_pulse.py` (pulse compiler), `test_heac_drc_lvs.py` (HEaC GDS/DRC/LVS), and `test_calibration.py` (digital twin calibration).

---

## Hardware CI

On push/PR to `protocols/`, `asic/`, `engineering/`, `apps/`, `state/`, or `tests/`, GitHub Actions runs:

1. **Unit tests** — `pytest tests/` (with pip cache)
2. **SCA/SAST** — pip-audit, npm audit, Bandit
3. **Container scan** — Trivy on API and frontend images; **SARIF upload** to GitHub Security tab and PR checks
4. **Pipeline + thermodynamic validation** — `run_pipeline.py -o ci_result --heac --fast`, then `thermodynamic_validator.py` on the generated phases
5. **GDS/manifest diff** (on PRs) — `engineering/ci_gds_diff.py` compares current run to `engineering/ci_baseline/`
6. **Push to ECR** (optional) — On push to `main`/`master`, if `ENABLE_ECR_PUSH=true` and `AWS_ROLE_TO_ASSUME` (OIDC) are set, images are built and pushed to Amazon ECR. See [deploy/README.md](deploy/README.md).

Store reference outputs in `engineering/ci_baseline/` (see `engineering/ci_baseline/README.md`) to enable diff comments.

---

## Whitepaper and reports

### Document guide

| If you want… | Read… |
|--------------|--------|
| **Vision, protocol layer, roadmap, and code** | [WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.md](docs/WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.md) |
| **Pulse-level control** (gate → schedule, OpenPulse, pseudo-schedule) | [PULSE_CONTROL.md](docs/PULSE_CONTROL.md) |
| **HEaC, PDK, DRC/LVS** | [HEaC_opensource_Meep.md](docs/HEaC_opensource_Meep.md) |
| **Thermal stages and parasitic extraction** | [THERMAL_AND_PARASITICS.md](docs/THERMAL_AND_PARASITICS.md) |
| **Digital twin calibration** | [CALIBRATION_DIGITAL_TWIN.md](docs/CALIBRATION_DIGITAL_TWIN.md) |
| **Channel noise and decoherence** | [CHANNEL_NOISE.md](docs/CHANNEL_NOISE.md) |
| **Math details** (QAOA, DNN phase synthesis) | [WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.tex](docs/WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.tex) (build PDF: see [docs/README.md](docs/README.md#building-pdfs-tex-live)) |
| **Full-stack diagram** | [docs/architecture_overview.md](docs/architecture_overview.md) |
| **Next steps / maturity roadmap** | [docs/NEXT_STEPS_ROADMAP.md](docs/NEXT_STEPS_ROADMAP.md) |
| **Roadmap implementation status** | [docs/ROADMAP_STATUS.md](docs/ROADMAP_STATUS.md) |

### Documents

- **[Holographic Metasurfaces as a Scalable Control Layer for Solid-State Quantum Entanglement and Secure SATCOM](docs/WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.md)** — Whitepaper: programmable metasurfaces as cryogenic quantum bus and for tamper-evident quantum SATCOM and phased-array quantum radar.
- **Cryogenic Metamaterial Architectures for Solid-State Quantum Routing and SATCOM** — Long-form LaTeX: [source](docs/Cryogenic_Metamaterial_Architectures_Quantum_SATCOM.tex). Covers rf-SQUIDs, LiNbO₃ BAW, Cryo-CMOS, QUBO/QAOA routing, DNN inverse design, quantum illumination, ecosystems.
- **Computational Materials Science and Simulation Architectures for Cryogenic Quantum Metamaterials** — LaTeX: [source](docs/Computational_Materials_Science_Cryogenic_Quantum_Metamaterials.tex).
- **Engineering as Code: A Distributed Computational Roadmap** — LaTeX: [source](docs/Engineering_as_Code_Distributed_Computational_Roadmap.tex).

Build all LaTeX PDFs: `.\docs\build_pdfs.ps1` from repo root (see [docs/README.md](docs/README.md#building-pdfs-tex-live)).

---

## References

- [Quirk: Quantum Circuit Simulator](https://algassert.com/quirk) — e.g. teleportation + "Thief" circuit.
- Mayers–Lo–Chau: no-go for unconditional quantum bit commitment.
- Micius satellite: space-based entanglement distribution and teleportation.
