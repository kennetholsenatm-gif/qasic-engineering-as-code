# QASIC Engineering-as-Code

**Repository:** [github.com/kennetholsenatm-gif/qasic-engineering-as-code](https://github.com/kennetholsenatm-gif/qasic-engineering-as-code)

**Quantum ASIC and Engineering-as-Code (EaC) pipeline:** protocols, routing, inverse design, quantum illumination, and CV quantum radar. Pedagogical implementations of **quantum teleportation**, **tamper-evident channels**, and **bit commitment** over a quantum link, plus DV/CV quantum illumination—in pure Python with NumPy.

**Status:** The full stack (protocols, routing, inverse design) runs **without physical metamaterials**: simulation and real IBM Quantum for routing, CPU/GPU for inverse design. Use `python engineering/run_pipeline.py` to run routing then inverse design in one go; see [Whitepaper §8 and §10](docs/WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.md).

## Concepts

| Protocol | What it demonstrates |
|----------|----------------------|
| **Entanglement & teleportation** | Bell pair creation, state transfer with classical message, no cloning. |
| **Tamper-evidence (Thief)** | Intercepting the "message" disturbs the state; receiver sees fidelity drop. |
| **Toy bit commitment** | Commit to a bit using shared entanglement + classical reveal; security relies on tamper-evident channel + bounded storage (toy assumptions). |
| **3-qubit bit-flip code** | Minimal QEC: encode one logical qubit, correct one bit-flip error on the ASIC linear chain. |
| **QKD (BB84 / E91)** | Pedagogical prepare-and-measure (BB84) and entanglement-based (E91) key distribution. |

## Security assumptions (toy)

- **No unconditional security.** The bit-commitment toy is *not* information-theoretically secure (Mayers–Lo–Chau no-go applies in the full model). We assume a **passive** adversary or **bounded quantum storage** so the protocol is binding/hiding in a pedagogical setting.
- **Perfect devices.** No channel loss, no detector noise—we're illustrating principles. For noisy links, use the **channel noise simulator** or **DV quantum illumination** (thermal loss channel). For physics-accurate microwave-style TMSV and thermal baths, use the **toy CV quantum radar** (covariance matrices); see [docs/CV_QUANTUM_RADAR.md](docs/CV_QUANTUM_RADAR.md).

## Quantum ASIC

The **Quantum ASIC** idea: reduce hardware to **only the gates and topology** needed for these protocols—no full connectivity, no universal gate set. One fixed “chip” spec:

- **3 qubits**, linear chain: `0 — 1 — 2` (only adjacent pairs can do CNOT).
- **Gates:** H, X, Z, CNOT (and optional Rx for the tamper model).

All three protocols compile to this minimal set and validate against it. See **[docs/QUANTUM_ASIC.md](docs/QUANTUM_ASIC.md)** for the spec and **`python demos/demo_asic.py`** to validate and run. For routing and visualization of other topologies (star, repeater chain), see **`asic/topology_builder`** and **[docs/TOPOLOGY_BUILDER.md](docs/TOPOLOGY_BUILDER.md)**.

## Applications

Two applications live under **`apps/`** and use the shared **`QRNG.PY`** at repo root where needed:

- **[BQTC](apps/README.md#bqtc-bayesian-quantum-traffic-controller)** — Bayesian-Quantum Traffic Controller: Telemetry → Bayesian inference → Qiskit QUBO path selection → VyOS BGP actuator.
- **[qrnc](apps/README.md#qrnc-quantum-backed-tokens-and-exchange)** — Quantum-backed tokens and BitCommit-style two-party exchange.

See [apps/README.md](apps/README.md) for run instructions and [docs/APPLICATIONS.md](docs/APPLICATIONS.md) for purpose and security caveats. Conceptual extensions to **data and control plane** (tamper-evident tunneling, FEC, key streaming, BGP commitment, SD-WAN QAOA, OAM fault localization) are described in [docs/DATA_AND_CONTROL_PLANE_QUANTUM_ASIC.md](docs/DATA_AND_CONTROL_PLANE_QUANTUM_ASIC.md).

## Project layout

```
qasic-engineering-as-code/
├── README.md
├── requirements.txt
├── QRNG.PY                    # Shared quantum RNG (used by apps/qrnc)
├── apps/                      # Applications: BQTC, qrnc
│   ├── README.md
│   ├── bqtc/                   # Bayesian-Quantum Traffic Controller
│   └── qrnc/                   # Quantum-backed tokens and exchange
├── docs/
│   ├── README.md             # Document index and "how to read" pointer
│   ├── architecture_overview.md   # Full-stack diagram: protocol → routing → inverse design → hardware → apps
│   ├── QUANTUM_ASIC.md       # ASIC spec: topology + gate set
│   ├── TOPOLOGY_BUILDER.md   # Named topologies (linear, star, repeater) + viz_topology
│   ├── CV_QUANTUM_RADAR.md   # Toy CV simulator: TMSV, covariance matrices, quantum radar
│   ├── WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.md
│   ├── WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.tex
│   └── Cryogenic_Metamaterial_Architectures_Quantum_SATCOM.tex  # Long-form LaTeX report
├── state/                    # Minimal qubit simulation + toy CV (Gaussian)
│   ├── __init__.py
│   ├── state.py              # State vectors, ket notation
│   ├── gates.py              # I, H, X, Z, CNOT, etc.
│   ├── channels.py           # Noise channels (Kraus: depolarizing, thermal loss, etc.)
│   ├── density.py            # DensityState, state_to_density, fidelity for mixed states
│   ├── cv_state.py           # GaussianState (covariance V, mean d), symplectic form
│   └── cv_gates.py           # Symplectic: two_mode_squeezing, beam_splitter (TMSV, loss)
├── asic/                     # Quantum ASIC: minimal gates + topology
│   ├── __init__.py
│   ├── topology.py           # Qubit count, allowed edges
│   ├── gate_set.py           # Allowed 1q/2q gates
│   ├── circuit.py            # Op list, validation, protocol_*_ops()
│   └── executor.py           # Run ASIC circuit on State
├── protocols/                # Protocol logic
│   ├── __init__.py
│   ├── entanglement.py       # Bell pairs, distribution
│   ├── teleportation.py      # Teleport one qubit
│   ├── tamper_evident.py     # Thief intercept → fidelity drop
│   ├── commitment.py         # Toy bit commitment
│   ├── noise.py              # NoiseModel, run_teleport_with_noise, run_thief_with_noise
│   ├── quantum_illumination.py  # DV toy: Bell probe vs thermal loss, Chernoff comparison
│   └── quantum_radar.py      # CV toy: TMSV + lossy thermal BS, mutual info, SNR; see docs/CV_QUANTUM_RADAR.md
├── engineering/               # Metasurface routing + inverse design (optional; no physical metasurface required)
│   ├── README.md
│   ├── requirements-engineering.txt
│   ├── routing_qubo_qaoa.py  # QUBO: logical qubits -> physical nodes (QAOA/classical); --topology linear|star|repeater
│   ├── metasurface_inverse_net.py  # PyTorch: target topology -> phase profile
│   ├── run_pipeline.py       # Run routing then inverse design (sim or --hardware)
│   ├── run_protocol_on_ibm.py  # Run ASIC protocol (teleport, Bell, etc.) on IBM or simulator
│   ├── viz_routing_phase.py  # Summarize routing JSON + phase array
│   └── viz_topology.py       # Draw topology graph (+ optional mapping from routing JSON); see docs/TOPOLOGY_BUILDER.md
├── dashboard/                # CLI dashboard (python -m dashboard)
│   ├── __main__.py
│   └── cli_dashboard.py      # Rich menu: run protocol/routing/pipeline, view results, docs
├── app/                      # FastAPI backend (uvicorn app.main:app)
│   ├── main.py               # API routes: run protocol/routing/pipeline/inverse, results, docs
│   └── requirements.txt
├── frontend/                 # Vite + React SPA (npm run dev / npm run build)
│   ├── src/
│   └── package.json
├── tests/                    # Pytest suite (state, protocols, ASIC, engineering, viz)
│   ├── conftest.py
│   ├── test_state.py
│   ├── test_protocols_*.py
│   ├── test_asic.py
│   ├── test_engineering_*.py
│   └── test_viz.py
├── demos/                    # Runnable scripts
    ├── demo_teleport.py
    ├── demo_thief.py
    ├── demo_commitment.py
    ├── demo_noise.py         # Teleport/tamper with channel noise (depolarizing, amplitude/phase damping)
    ├── demo_asic.py          # Validate protocols on ASIC, run teleport
    ├── demo_bitflip_code.py  # 3-qubit bit-flip repetition code (QEC)
    ├── demo_bb84.py          # BB84 QKD
    └── demo_e91.py           # E91 QKD (Bell + CHSH)
```

### Channel noise and decoherence

To simulate **environmental degradation** (atmospheric attenuation, thermal fluctuations, detector inefficiency), use the noise simulator:

- **`state/channels.py`**: Kraus channels (depolarizing, amplitude/phase damping, thermal, detector loss).
- **`protocols/noise.py`**: `NoiseModel`, `run_teleport_with_noise`, `run_thief_with_noise` with configurable injection points.
- **`python demos/demo_noise.py`**: Run teleport and tamper with noise; compare fidelity drop from noise vs tampering.

See **[docs/CHANNEL_NOISE.md](docs/CHANNEL_NOISE.md)** for formulas and usage.

## Quick start

Run from the **repo root** (use `py` or `python` as on your system; on Windows you may need `py` if `python` is not on PATH):

```bash
git clone https://github.com/kennetholsenatm-gif/qasic-engineering-as-code.git
cd qasic-engineering-as-code
pip install -r requirements.txt
python demos/demo_teleport.py
python demos/demo_thief.py
python demos/demo_commitment.py
python demos/demo_noise.py    # Channel noise (depolarizing, amplitude/phase damping)
python demos/demo_asic.py     # Quantum ASIC: gates + topology
python demos/demo_bitflip_code.py   # 3-qubit bit-flip repetition code (QEC)
python demos/demo_bb84.py           # BB84 QKD (pedagogical)
python demos/demo_e91.py            # E91 QKD (Bell pairs + CHSH)
```

Demos are script-style (no CLI arguments). For the full pipeline (routing + inverse design), run `python engineering/run_pipeline.py`; it writes `engineering/<base>_routing.json`, `engineering/<base>_inverse.json`, and `engineering/<base>_inverse_phases.npy` (default base: `pipeline_result`). Use `--routing-method rl` for RL-based routing or `--model gnn` for GNN inverse design; use `--with-superscreen` to compute inductance from the routing topology (optional). For affordable runs on IBM Quantum (under 5 minutes QPU time), see [Engineering as Code on IBM Quantum](engineering/README.md#engineering-as-code-on-ibm-quantum-affordable-5-min) in the engineering README.

### Docker

Run the API, frontend, and optional Jupyter in one go:

```bash
docker-compose up --build
```

Then open the frontend at `http://localhost` (or port 80). For Jupyter: `docker-compose --profile jupyter run --service-ports jupyter`.

## CLI dashboard

A terminal menu lets you run protocols, routing, pipeline, and inverse design and view last results without the web app:

```bash
pip install -r requirements-dashboard.txt
python -m dashboard
```

Or `python dashboard/cli_dashboard.py` from the repo root. Options: run protocol (sim or IBM hardware), run routing (sim or IBM fast), run full pipeline (sim), run inverse design, view last results, show doc links. See [dashboard/](dashboard/).

## Web app

A browser UI is provided by the FastAPI backend and the front end SPA. From repo root: install backend deps (`pip install -r app/requirements.txt`), start the API (`uvicorn app.main:app --reload`), then run the front end (`cd frontend && npm install && npm run dev`) or build and serve the SPA from the backend. See [app/README.md](app/README.md) and [frontend/README.md](frontend/README.md).

- **Phase viewer (3D):** In the app, open "Phase viewer (3D)" to view the latest inverse-design phase profile as an interactive 3D surface (requires running pipeline or inverse design first).
- **Async IBM jobs:** When you run a protocol on IBM hardware, the API returns a `job_id` and the UI connects via WebSocket to show live status (Queued → Running → Done) and the result when ready.

## Testing

From the repo root:

```bash
pip install -r requirements-test.txt
python -m pytest tests/ -v
```

Optional: install `engineering/requirements-engineering.txt` to run routing and inverse-net tests (including `test_engineering_routing.py` QUBO build when `qiskit-optimization` is available).

## Whitepaper and reports

### Document guide

| If you want… | Read… |
|--------------|--------|
| **Vision, protocol layer, roadmap, and code** (architecture overview, Quantum ASIC, routing/inverse-design commands) | [WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.md](docs/WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.md) |
| **Math details** (QAOA mixing Hamiltonian, DNN phase synthesis, key equations) | [WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.tex](docs/WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.tex) (short LaTeX; build PDF: see [Building PDFs](docs/README.md#building-pdfs-tex-live)) |
| **Materials, cryo hardware, ecosystems** (rf-SQUIDs, LiNbO₃ BAW, Cryo-CMOS Gooseberry, San Diego ecosystem) | [Cryogenic_Metamaterial_Architectures_Quantum_SATCOM.tex](docs/Cryogenic_Metamaterial_Architectures_Quantum_SATCOM.tex) (long LaTeX report; build PDF: same) |
| **Code-based materials science, simulation tools, cost-effective infra** (scqubits, SuperScreen, QuTiP, QAOA, potential partners) | [Computational_Materials_Science_Cryogenic_Quantum_Metamaterials.tex](docs/Computational_Materials_Science_Cryogenic_Quantum_Metamaterials.tex) (LaTeX report; build PDF: same) |
| **Engineering as Code distributed roadmap** (virtualized quantum hardware, HPC/simulation stack, QAOA, DNN surrogates, cost-effective infra, potential partners) | [Engineering_as_Code_Distributed_Computational_Roadmap.tex](docs/Engineering_as_Code_Distributed_Computational_Roadmap.tex) (LaTeX report; build PDF: same) |
| **Full-stack diagram** (protocol → routing → inverse design → hardware → apps) | [docs/architecture_overview.md](docs/architecture_overview.md) |

### Documents

- **[Holographic Metasurfaces as a Scalable Control Layer for Solid-State Quantum Entanglement and Secure SATCOM](docs/WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.md)** — Expanded whitepaper on using programmable metasurfaces as a cryogenic quantum bus (on-chip) and for weather-resilient, tamper-evident quantum SATCOM and phased-array quantum radar. Ties the protocol layer (minimal topology, Quantum ASIC) to the hardware vision.
- **Cryogenic Metamaterial Architectures for Solid-State Quantum Routing and SATCOM** — Long-form LaTeX report: [source](docs/Cryogenic_Metamaterial_Architectures_Quantum_SATCOM.tex). Covers thermodynamic bottleneck, rf-SQUIDs, lithium niobate BAW, 28nm FD-SOI Cryo-CMOS, QUBO/QAOA routing, DNN inverse design, quantum SATCOM/radiative cooling, quantum illumination, and regional ecosystems. With TeX Live installed, run `.\docs\build_pdfs.ps1` from repo root to build all LaTeX PDFs (see [docs/README.md](docs/README.md#building-pdfs-tex-live)).
- **Computational Materials Science and Simulation Architectures for Cryogenic Quantum Metamaterials** — LaTeX report: [source](docs/Computational_Materials_Science_Cryogenic_Quantum_Metamaterials.tex). Covers code-based materials science, protocol-layer logic, scqubits/SuperScreen/QuTiP/QAOA simulation stack, DNN surrogate modeling, quantum SATCOM/radar, hardware–software co-design ecosystems (identifying potential partners), and cost-effective computational infrastructure. Build with `.\docs\build_pdfs.ps1`.
- **Engineering as Code: A Distributed Computational Roadmap for Cryogenic Quantum Metamaterials and SATCOM Architectures** — LaTeX report: [source](docs/Engineering_as_Code_Distributed_Computational_Roadmap.tex). Covers virtualized quantum hardware imperative, software-defined topology and restricted gate sets, computational electrodynamics (scqubits, SuperScreen), open quantum systems and TLS mitigation, QAOA spatial routing, DNN surrogates for metasurface control, target ecosystems (identifying potential partners), and cost-effective computational infrastructure. Build with `.\docs\build_pdfs.ps1`.

## References

- [Quirk: Quantum Circuit Simulator](https://algassert.com/quirk) — e.g. teleportation + "Thief" circuit.
- Mayers–Lo–Chau: no-go for unconditional quantum bit commitment.
- Micius satellite: space-based entanglement distribution and teleportation.
