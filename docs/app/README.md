# Docs

Documentation and whitepapers for **QASIC Engineering-as-Code** ([GitHub](https://github.com/kennetholsenatm-gif/qasic-engineering-as-code)). For quick start and repo layout, see the [main README](../../README.md).

## Document index

| Document | Description |
|----------|-------------|
| [APPLICATIONS.md](APPLICATIONS.md) | **Applications:** BQTC (traffic control) and qrnc (quantum-backed tokens, exchange); run instructions and security caveats |
| [THEORETICAL_APPLICATIONS.md](THEORETICAL_APPLICATIONS.md) | **Theoretical applications:** Summary of Quantum ASIC protocols and how data-plane/control-plane concepts (MACsec, BGP commitment, SD-WAN QAOA, quantum illumination) map to existing code and docs |
| [DATA_AND_CONTROL_PLANE_QUANTUM_ASIC.md](DATA_AND_CONTROL_PLANE_QUANTUM_ASIC.md) | **Data and control plane extensions:** Low-qubit ASIC applications in data plane (MACsec/tamper-evident tunneling, FEC, key streaming) and control plane (BGP commitment, SD-WAN QAOA, OAM fault localization); links to demos and apps |
| [Graph_Theoretic_Inverse_Design_GNN_Metasurfaces.tex](Graph_Theoretic_Inverse_Design_GNN_Metasurfaces.tex) | **LaTeX whitepaper:** Graph-theoretic inverse design; GNNs for scaling quantum metamaterial topologies; thermodynamic constraints, $\pi$-radian baseline, MLP vs.\ GNN benchmarking |
| [Automated_HEaC_Deep_Cryogenic_Quantum_ASICs.tex](Automated_HEaC_Deep_Cryogenic_Quantum_ASICs.tex) | **LaTeX whitepaper:** Hardware-Engineering-as-Code (HEaC) for deep-cryogenic (10\,mK) Quantum ASICs; phase-to-geometry (CadQuery, PyAEDT, Meep), GDSII/DRC/LVS (gdsfactory, OpenROAD), PCB (KiCad, scikit-rf), fab package (Sphinx, thermal budget, ATPG) |
| [HEaC_opensource_Meep.md](HEaC_opensource_Meep.md) | **HEaC open-source (Meep):** Tool chain summary—meta-atom library (Meep sweep), phase-to-dimension, phases.npy → geometry manifest, optional GDSII (gdsfactory) |
| [Whitepaper_Unified_Quantum_Metasurfaces_SATCOM.tex](Whitepaper_Unified_Quantum_Metasurfaces_SATCOM.tex) | **Unified whitepaper (LaTeX):** EaC for Quantum ASICs; protocol, simulation, routing, applications |
| [Whitepaper_Unified_Quantum_Metasurfaces_SATCOM.md](Whitepaper_Unified_Quantum_Metasurfaces_SATCOM.md) | (Unified; see .tex for canonical source) |
| [Whitepaper_Infrastructure_Aware_Application.md](../research/Whitepaper_Infrastructure_Aware_Application.md) | **Markdown:** Infrastructure-Aware Application (IAA): dynamic topology-responsive systems, OpenTofu–Helm–FastAPI bridge, capabilities-driven UI, security and performance; aligns with [INFRASTRUCTURE_FEATURES.md](INFRASTRUCTURE_FEATURES.md) |
| [architecture_overview.md](architecture_overview.md) | Full-stack diagram: protocol layer → routing → inverse design → hardware → applications |
| [NEXT_STEPS_ROADMAP.md](NEXT_STEPS_ROADMAP.md) | **Next steps / maturity roadmap:** Tapeout (superconducting extraction, DFT, Monte Carlo), control/HIL (QICK, HIL CI), cryogenic (thermal→decoherence, Cryo-CMOS), interop (OpenQASM/QIR, GDS–MEEP pipeline), cryo packaging (2D→3D CAD, FEA, flex routing, magnetic shielding), metasurface physics (full-wave macro-sim, physics-informed GNN, cryogenic materials, active/spatiotemporal metasurfaces), control methodologies (GRAPE/CRAB, MIMO cancellation, System ID, dynamic metasurface control), fault tolerance & noise (QEC-aware routing, correlated error/TLS, Purcell filters, Stim/PyMatching LER) |
| [QKD.md](QKD.md) | **QKD:** Pedagogical BB84 and E91 (basis angles, CHSH); code and API |
| [QUANTUM_ASIC.md](QUANTUM_ASIC.md) | Quantum ASIC reference spec (minimal topology, gate set) and pipeline (any OpenQASM, any qubit count) |
| [OPENQASM_TO_ASIC_PIPELINE.md](OPENQASM_TO_ASIC_PIPELINE.md) | **OpenQASM 2/3 → ASIC:** Pipeline stages (parse → gate set → topology → geometry → extraction → manifest → routing → HEaC → GDS), file paths, pain points; 2.0 supported, 3.0 when qiskit-qasm3-import installed |
| [QISKIT_FUNCTIONS_IBM.md](QISKIT_FUNCTIONS_IBM.md) | **Run on IBM and Qiskit Functions:** Extending Run on IBM with Qiskit Functions for error mitigation and workload summaries; link to IBM blog and catalog |
| [OPENQASM_TO_ASIC_WUI_WALKTHROUGH.md](OPENQASM_TO_ASIC_WUI_WALKTHROUGH.md) | **OpenQASM 2/3 → digital-twin ASIC (WUI):** Step-by-step walkthrough for taking any OpenQASM 2/3 file (any qubit count) to digital-twin Quantum ASIC |
| [WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.md](WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.md) | Main whitepaper (Markdown): vision, protocol layer, roadmap, §10 supporting code |
| [WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.tex](WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.tex) | Short LaTeX paper + math appendix (QAOA, DNN phase synthesis) |
| [Cryogenic_Metamaterial_Architectures_Quantum_SATCOM.md](Cryogenic_Metamaterial_Architectures_Quantum_SATCOM.md) | **Markdown:** Cryogenic metamaterials, rf-SQUIDs, BAW, Cryo-CMOS, SATCOM (GitHub-friendly) |
| [Cryogenic_Metamaterial_Architectures_Quantum_SATCOM.tex](Cryogenic_Metamaterial_Architectures_Quantum_SATCOM.tex) | Full LaTeX report |
| [Computational_Materials_Science_Cryogenic_Quantum_Metamaterials.md](Computational_Materials_Science_Cryogenic_Quantum_Metamaterials.md) | **Markdown:** Code-based materials science, simulation stack (GitHub-friendly) |
| [Computational_Materials_Science_Cryogenic_Quantum_Metamaterials.tex](Computational_Materials_Science_Cryogenic_Quantum_Metamaterials.tex) | Full LaTeX report |
| [Engineering_as_Code_Distributed_Computational_Roadmap.md](Engineering_as_Code_Distributed_Computational_Roadmap.md) | **Markdown:** EaC distributed roadmap (GitHub-friendly) |
| [Engineering_as_Code_Distributed_Computational_Roadmap.tex](Engineering_as_Code_Distributed_Computational_Roadmap.tex) | Full LaTeX report |
| [quantum-terrestrial-backhaul.md](quantum-terrestrial-backhaul.md) | **Markdown:** Quantum-secured terrestrial P2P backhaul, metamaterials, QI, radiative cooling (GitHub-friendly) |
| [quantum-terrestrial-backhaul.tex](quantum-terrestrial-backhaul.tex) | Full LaTeX report |
| [PULSE_CONTROL.md](PULSE_CONTROL.md) | Gate → pulse schedule (OpenPulse / pseudo); pulse compiler usage |
| [THERMAL_AND_PARASITICS.md](THERMAL_AND_PARASITICS.md) | Thermal stages (10 mK / 4 K / 50 K), parasitic extraction, decoherence feedback |
| [CALIBRATION_DIGITAL_TWIN.md](CALIBRATION_DIGITAL_TWIN.md) | Telemetry → digital twin → decoherence for routing/simulation |
| [CHANNEL_NOISE.md](CHANNEL_NOISE.md) | Kraus channels, noise simulator (depolarizing, amplitude/phase damping, thermal) |
| [CV_QUANTUM_RADAR.md](CV_QUANTUM_RADAR.md) | Toy CV simulator: TMSV, covariance matrices, quantum radar |
| [TOPOLOGY_BUILDER.md](TOPOLOGY_BUILDER.md) | Named topologies (linear, star, repeater), viz_topology, get_topology API |
| [ROADMAP_STATUS.md](ROADMAP_STATUS.md) | Roadmap implementation status (done vs scaffold vs future) |
| **Program and roadmap** | |
| [ALPHA_SCOPE.md](ALPHA_SCOPE.md) | **Alpha scope:** In/out for Alpha; pipeline: any OpenQASM 2/3, any qubit count → digital-twin ASIC; computation-time warnings; parked items |
| [ALPHA_CUSTOMER.md](ALPHA_CUSTOMER.md) | **Alpha focus:** Primary use case (digital-twin pipeline, solo developer) |
| [ROADMAP_SCHEDULE.md](ROADMAP_SCHEDULE.md) | **Roadmap schedule:** Phases 3–4 timeline, dependencies, owners (TBD) |
| [PROGRAM_ACTION_ITEMS.md](PROGRAM_ACTION_ITEMS.md) | **Action items and prioritization:** Deliverables and next steps |
| **Architecture and risk** | |
| [ARCHITECTURE_CONTROL_VS_DATA_PLANE.md](ARCHITECTURE_CONTROL_VS_DATA_PLANE.md) | **Control vs data plane:** Proposal to split slim API (control) and heavy workers (data); current state and benefits |
| [ARCHITECTURE_MODULARIZATION_PROPOSAL.md](ARCHITECTURE_MODULARIZATION_PROPOSAL.md) | **Modularization:** Proposal for qasic-ui, qasic-orchestrator, qasic-compute-workers; deploy boundaries and migration path |
| [SIMULATION_VALIDATION_STRATEGY.md](SIMULATION_VALIDATION_STRATEGY.md) | **Sim–fab validation:** How FDTD and thermal-to-decoherence will be validated against real data; first silicon plan |
| [COMPUTE_COST_ASSESSMENT.md](COMPUTE_COST_ASSESSMENT.md) | **Compute cost:** Cost and margin for DAGs (local, IBM, EKS); budget guardrail; placeholder cost table |
| [PIPELINE_METRICS.md](PIPELINE_METRICS.md) | **Pipeline metrics:** Metrics to track (GDS success rate, latency, failure rate); bi-weekly review template |
| [DATA_PERSISTENCE.md](DATA_PERSISTENCE.md) | Data persistence (MLflow, InfluxDB, Postgres) for pipeline and app |
| [ORCHESTRATION.md](ORCHESTRATION.md) | Prefect 2 DAG for pipeline and calibration; retries and server |
| [superscreen_integration.md](superscreen_integration.md) | SuperScreen 2D London equation / Meissner screening integration |

**How to read:** Each whitepaper has a **Markdown (.md)** version for GitHub and quick reading; the **LaTeX (.tex)** source is for full equations and PDF build. For vision and protocols → [WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.md](WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.md). For EaC roadmap, cryogenic metamaterials, computational materials science, and terrestrial backhaul → use the corresponding .md files above. See the main [README](../../README.md) for repo layout.

### Building PDFs (TeX Live)

All LaTeX sources are intended to be compiled with **XeLaTeX** (Noto Sans, Unicode). The documents use `babel` with `bidi=bidi` for XeLaTeX compatibility (do not use `bidi=basic`, which is LuaTeX-only). With [TeX Live](https://tug.org/texlive/) installed and `xelatex` on your PATH (if you just installed TeX Live, open a new terminal or add TeX Live’s `bin` folder to PATH, e.g. `C:\texlive\2024\bin\windows`):

- **From repo root:**  
  `.\docs\research\build_pdfs.ps1`  
  This builds all LaTeX PDFs (two passes each for references) and writes them in `docs/research/`.
- **Manual (from `docs/research/`):**  
  `xelatex WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.tex` (run twice), then the same for other .tex files.
