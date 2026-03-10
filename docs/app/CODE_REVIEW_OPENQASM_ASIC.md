# Code Review: ASIC Circuit Always openQASM-Derivative

**Goal:** Ensure the quantum circuit for the ASIC is never statically defined in code; it should always be derivable from openQASM (OpenQASM 2.0 or 3.0). The **circuit-driven** pipeline builds topology from OpenQASM (any qubit count); `DEFAULT_TOPOLOGY` is for demos/fallback only.

---

## Summary

| Area | Status | Notes |
|------|--------|--------|
| **Algorithm-to-ASIC pipeline** | ✅ Compliant | `qasm_to_asic_pipeline.py` and backend only accept `qasm_path` or `qasm_string`; no static circuit. |
| **Run Pipeline (app/Celery)** | ✅ Compliant | Requires `qasm_string`; topology and routing are derived from QASM interaction graph. |
| **qasm_loader** | ✅ Compliant | All entry points are QASM (string or path) → ops or interaction graph. |
| **topology_builder** | ✅ Compliant | Topology and geometry manifest built from interaction graph (from QASM); `library_source: "qasm_to_asic"`. |
| **Static protocol ops** | ⚠️ Non-compliant | `circuit.py` defines `protocol_teleport_ops()`, `protocol_commitment_ops()`, `protocol_thief_ops()`, `protocol_bitflip_code_ops()` as hardcoded Python. |
| **Pulse compile CLI** | ⚠️ Non-compliant | Accepts only named circuits (teleport, commitment, thief) or JSON path; no `.qasm` input. |
| **Run protocol on IBM** | ⚠️ Non-compliant | Uses `get_protocol_ops(protocol)` with static ops only; no QASM input. |
| **DEFAULT_TOPOLOGY** | ⚠️ Contextual | Static 3-qubit linear in `topology.py`; used for validation/demos when no topology is passed. Pipeline path builds topology from QASM. |

---

## Compliant Paths (no static circuit)

- **`src/core_compute/engineering/qasm_to_asic_pipeline.py`**  
  `run_qasm_to_asic(qasm_path=..., qasm_string=...)` — requires one of them; no default circuit.

- **`src/backend/main.py`**  
  Run Pipeline requires `project_id` and `qasm_string`; `_require_project_and_circuit()` enforces no default circuit. Validation uses `interaction_graph_from_qasm_string()`.

- **`src/backend/tasks.py`**  
  `circuit_to_asic_task` and `run_pipeline_with_circuit_task` take `qasm_string`; routing uses graph from `run_qasm_to_asic(..., qasm_string=...)`.

- **`src/core_compute/asic/qasm_loader.py`**  
  `load_qasm_string`, `load_qasm`, `interaction_graph_from_qasm_string`, `interaction_graph_from_qasm_path` — all inputs are openQASM.

- **`src/core_compute/asic/topology_builder.py`**  
  `build_topology_from_interaction_graph(graph)` and `geometry_manifest_from_interaction_graph(graph)` use the graph produced from QASM; manifest has `"library_source": "qasm_to_asic"`.

---

## Non-compliant / Legacy Paths

### 1. `src/core_compute/asic/circuit.py`

**Issue:** Defines static op lists:

- `protocol_teleport_ops()`
- `protocol_commitment_ops()`
- `protocol_thief_ops(qubit, angle)`
- `protocol_bitflip_code_ops(include_error_qubit)`

These are **reference/demo implementations** for protocols. They are **not** used by the Algorithm-to-ASIC or Run Pipeline paths, but they are used by:

- `run_protocol_on_ibm.py` (protocol-on-IBM)
- `pulse/compile_cli.py` (named circuit or JSON)
- `demos/demo_asic.py`, `executor.py` `__main__`, tests

**Recommendation:** Treat these as demos only. Prefer loading circuits from openQASM everywhere else. Optionally add canonical `.qasm` files (e.g. under `demos/` or `config/`) for teleport, commitment, thief, bitflip and load from them so even “named” circuits are openQASM-derived.

### 2. `src/core_compute/pulse/compile_cli.py`

**Issue:** `load_circuit_ops(spec)` accepts:

- Named circuits: `teleport`, `commitment`, `thief` (→ static ops from `circuit.py`)
- Path to JSON (ops list)

No support for a `.qasm` file or QASM string, so pulse compilation can be invoked without openQASM.

**Recommendation:** Add `--qasm <path>` and/or accept a path that ends in `.qasm` in `--circuit`, and load ops via `load_qasm_string(Path(path).read_text())` or `load_qasm(path)` from `qasm_loader`. Keep named circuits as shortcuts for demos, but document that the canonical source is openQASM.

### 3. `src/core_compute/engineering/run_protocol_on_ibm.py`

**Issue:** `get_protocol_ops(protocol)` returns only static ops for `teleport`, `bell`, `commitment`, `thief`. No option to pass QASM; protocol circuit is never openQASM-derived.

**Recommendation:** For consistency, add an optional path to accept QASM (e.g. `qasm_string` or path) and build ops via `load_qasm_string` / `load_qasm`, with named protocols as convenience for demos.

### 4. `src/core_compute/asic/topology.py` — `DEFAULT_TOPOLOGY`

**Issue:** `DEFAULT_TOPOLOGY` is a fixed 3-qubit linear chain. Used by `ASICCircuit` and `validate_circuit()` when no topology is passed.

**Context:** In the pipeline, topology is built from the QASM-derived interaction graph, so the pipeline never relies on `DEFAULT_TOPOLOGY` for the ASIC circuit definition. The default is only for standalone validation, demos, and tests.

**Recommendation:** Document that `DEFAULT_TOPOLOGY` is for validation/demos only; the production ASIC topology is always from openQASM (interaction graph → `build_topology_from_interaction_graph`).

---

## Standalone `run_pipeline.py` (no circuit)

When run **without** the backend (CLI only), `run_pipeline.py` runs routing with default topology (e.g. `--qubits 3`, default `linear_chain`). That path does **not** take a circuit/QASM; it is a separate use case (e.g. testing routing + inverse with a fixed topology). The **circuit-driven** path is always via the app/Celery with `qasm_string`, which is openQASM-derived.

---

## Checklist for “circuit always openQASM-derivative”

- [x] Algorithm-to-ASIC: only QASM input.
- [x] Backend Run Pipeline: requires `qasm_string`; no default circuit.
- [x] Topology/geometry in pipeline: from interaction graph (from QASM).
- [x] Pulse compile CLI: add QASM path so compilation can be openQASM-only when desired (--circuit accepts .qasm/.qasm2/.qasm3 path).
- [ ] Protocol-on-IBM: optional QASM input for consistency (named protocols remain as demos).
- [x] Document `protocol_*_ops()` and `DEFAULT_TOPOLOGY` as reference/demo only; production circuit = openQASM (see circuit.py and topology.py docstrings).
