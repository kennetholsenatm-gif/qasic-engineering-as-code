# OpenQASM to Quantum ASIC Pipeline

This document describes the **step-by-step process** from an OpenQASM file to a Quantum ASIC, with file paths and **pain points** to expect. It aligns with the plan "OpenQASM 3.0 to Quantum ASIC: Step-by-Step Process and Pain Points."

## Supported versions

- **OpenQASM 2.0:** Supported today. Parsed via built-in regex or `qiskit.qasm2` when available.
- **OpenQASM 3.0:** Supported when `qiskit-qasm3-import` is installed (`pip install qiskit-qasm3-import`). Version is auto-detected from the first declaration line (`OPENQASM 2.0;` vs `OPENQASM 3.0;`).

Optional **decomposition** to the ASIC gate set (T, S, Rz, U3, etc. → H, X, Z, Rx, CNOT) is available via `decompose_to_asic=True` in `load_qasm_string`, `load_qasm`, and `interaction_graph_from_qasm_string` / `interaction_graph_from_qasm_path` when using the Qiskit path (3.0 or 2.0 from file).

---

## Pipeline stages (chain)

| Stage | Description | Key files / entry points |
|-------|-------------|--------------------------|
| **1. QASM → parse** | Parse and validate OpenQASM 2 or 3 source; produce operation list. | `src/core_compute/asic/qasm_loader.py`: `load_qasm_string`, `load_qasm`, `_detect_qasm_version` |
| **2. Gate set mapping** | Map or decompose to ASIC gates (H, X, Z, Rx, CNOT). Reject or transpile unsupported gates. | `qasm_loader.py`: `_quantum_circuit_to_ops`, `_transpile_to_asic_basis`; `asic/gate_set.py` |
| **3. Interaction graph** | Build undirected graph of qubit pairs that interact (2-qubit gates). | `qasm_loader.py`: `interaction_graph_from_ops`, `interaction_graph_from_qasm_string`, `interaction_graph_from_qasm_path` |
| **4. Topology + geometry** | From interaction graph, build Topology and geometry manifest (positions, pitch). | `src/core_compute/asic/topology_builder.py`: `build_topology_from_interaction_graph`, `geometry_manifest_from_interaction_graph` |
| **5. Superconducting extraction** | Extract kinetic inductance, etc.; produce custom ASIC manifest. | `src/core_compute/engineering/qasm_to_asic_pipeline.py`: `run_qasm_to_asic`; `superconducting_extraction.py` |
| **6. Routing** | Control-line and resource assignment (optional; circuit-derived routing). | `src/core_compute/engineering/routing_rl.py`, `routing_qubo_qaoa`; pipeline combines qasm_to_asic + routing |
| **7. Inverse + HEaC** | Inverse design, phase-to-geometry, optional GDS. | `src/core_compute/engineering/run_pipeline.py`; `heac/manifest_to_gds.py`, `phases_to_geometry.py` |
| **8. GDS / layout** | 2D lithography output. 3D packaging is a separate step. | `engineering/heac/manifest_to_gds.py`; roadmap §5 for packaging |

End-to-end entry: **Algorithm-to-ASIC** → `run_qasm_to_asic` (QASM string or path → interaction graph → topology → geometry manifest → superconducting extraction → custom ASIC manifest). Full pipeline with circuit-driven routing → backend `run_mode=circuit_pipeline` + `qasm_string` (Celery task) or `run_pipeline.py` with routing inputs.

---

## Pain points (checklist)

| Area | Pain point |
|------|------------|
| **Input** | OpenQASM 3.0 requires `qiskit-qasm3-import`. Without it, 3.0 source raises a clear `QasmParseError`. File extension is often `.qasm` for both 2.0 and 3.0; version is determined by the first declaration line. |
| **Gates** | ASIC supports only **H, X, Z, Rx, CNOT**. Unsupported gates (T, S, Rz, U3, etc.) cause rejection unless `decompose_to_asic=True` is used (Qiskit path only). Decomposition can increase depth and 2-qubit count. |
| **Parsing** | OpenQASM 3.0 has multiple parsers (QE-Compiler, Shipyard, Qiskit). This repo uses `qiskit.qasm3` when `qiskit-qasm3-import` is installed. Not all 3.0 language features (e.g. `defcal`, full control flow) may be supported by every parser. |
| **Topology** | Topology is derived from the **circuit’s interaction graph** (which pairs have 2-qubit gates). There is no built-in “fixed hardware graph + minimal SWAP” layout synthesis; for a fixed chip connectivity, external layout synthesis (e.g. ML-SABRE, EDA-Q) would be needed. |
| **Pulses** | Gate-based pulse path exists (`pulse/compiler.py`). OpenQASM 3.0 `defcal` and vendor control stacks (e.g. Zurich via Shipyard) are separate ecosystems. |
| **GDS / packaging** | Pipeline produces 2D GDS. 3D packaging (cryogenic sample holder, flex routing, shielding) is documented in roadmap §5 and implemented as stubs or separate modules. |
| **Verification** | No single end-to-end formal equivalence check from OpenQASM to GDS. Validation relies on the chain (parse → gate set → topology → geometry → extraction → GDS) plus separate thermal/EM runs. |
| **Ops** | Full circuit-driven pipeline in the app (run_mode=circuit_pipeline) uses Celery/Redis; configuration and environment must be set for async execution. |

---

## Quick reference: code entry points

- **Parse QASM string:** `load_qasm_string(qasm_text, decompose_to_asic=False)` → `list[Op]`
- **Parse QASM file:** `load_qasm(path, decompose_to_asic=False)` → `list[Op]`
- **Interaction graph from string:** `interaction_graph_from_qasm_string(qasm_text, decompose_to_asic=False)` → `nx.Graph`
- **Full Algorithm-to-ASIC:** `run_qasm_to_asic(qasm_string=..., qasm_path=..., output_dir=..., ...)` → dict with custom ASIC manifest paths and extraction result

See `src/core_compute/asic/qasm_loader.py` and `src/core_compute/engineering/qasm_to_asic_pipeline.py` for implementation details.

---

## Version and reproducibility

- **OpenQASM spec:** 2.0 and 3.0 as per [openqasm.com](https://openqasm.com/). Version is detected from the first declaration line in the source.
- **Parser / runtime:** OpenQASM 2.0 uses the built-in regex parser or `qiskit.qasm2` (from `qiskit>=2.0`). OpenQASM 3.0 uses `qiskit.qasm3` from the optional package `qiskit-qasm3-import>=0.5.0` (see `pyproject.toml` and `src/core_compute/engineering/requirements-engineering.txt`).
- **CI:** The workflow `.github/workflows/hardware-ci.yml` includes a job **OpenQASM 2.0 / 3.0 → ASIC pipeline** that runs a small 2.0 and 3.0 example through `run_qasm_to_asic` to catch regressions. Pin these versions in your environment for reproducible builds.
