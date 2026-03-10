# OpenQASM 2/3 → Digital-Twin Quantum ASIC: WUI Walkthrough and Pain Points

This document walks through the **web UI (WUI)** path for taking **any OpenQASM 2 or 3 file (any qubit count)** to a **digital-twin Quantum ASIC** using [qasic-engineering-as-code](https://github.com/kennetholsenatm-gif/qasic-engineering-as-code). Every step and **pain point** is noted so product and engineering can improve the flow. For large circuits, expect longer pipeline runs; see [OPENQASM_TO_ASIC_PIPELINE.md](OPENQASM_TO_ASIC_PIPELINE.md) for computation-time guidance.

---

## Prerequisites (before opening the WUI)

1. **Stack running**
   - From repo root: `docker compose up -d --build` (or copy `.env.example` to `.env` first on Windows: `copy .env.example .env`).
   - Wait ~30s for API healthcheck. Check: `docker compose ps` — all services (api, frontend, celery-worker, redis, postgres) should be "Up".
2. **OpenQASM 3.0 support (backend)**
   - OpenQASM 3.0 parsing requires `qiskit-qasm3-import`. The API Docker image is built from `Dockerfile.api`; ensure the install includes `pip install -e ".[engineering]"` or the dependency from `src/core_compute/engineering/requirements-engineering.txt` so the backend can parse 3.0. If 3.0 fails with a parse error, the backend may be missing this optional dependency.

**Pain point — Discovery:** There is no WUI screen that says "OpenQASM 3.0 is supported" or "Install qiskit-qasm3-import for 3.0". Users may try 3.0 and only see a generic "Invalid QASM" (or the detailed error if `QASIC_DEBUG=1`).

---

## Step 1: Open the app

1. Open **http://localhost** (port 80). If you changed the frontend port (e.g. 8080), use that.
2. If the page does not load: ensure Docker is running, `docker compose ps`, and check [README.md](../../README.md) (ERR_CONNECTION_REFUSED, port in use).

**Pain point — First-time:** No in-app "Getting started" or "OpenQASM → ASIC" path is highlighted. The path is: Home → **Run full pipeline** (card: "Routing then inverse design in one run").

---

## Step 2: Go to "Run full pipeline"

1. On the home page, click the **Run full pipeline** card (or navigate to **/run/pipeline**).
2. You should see:
   - **DAG** section with tabs: "Pipeline (DevOps)" and "Circuit Topology (EaC)".
   - **Quantum circuit (optional)** section with an editor and "Paste OpenQASM 2 or drop a .qasm file…".

**Pain point — Copy:** The UI says "Paste OpenQASM **2** or drop a .qasm file". OpenQASM **3.0** is supported by the backend when `qiskit-qasm3-import` is installed; the label is misleading for 3.0-only users.

---

## Step 3: Provide your OpenQASM 2 or 3 circuit

**Any qubit count is supported.** Topology is derived from the circuit; the pipeline produces a digital-twin Quantum ASIC from your input.

1. **Option A — Paste:** Paste your OpenQASM 2.0 or 3.0 source into the editor. The first line must be `OPENQASM 2.0;` or `OPENQASM 3.0;` (version is auto-detected).
2. **Option B — File:** Click **Upload .qasm file** or drag-and-drop a `.qasm` / `.qasm2` file onto the editor. The file content replaces the editor content; the UI shows "File loaded: &lt;name&gt;".

For large circuits, runtimes may be long; see [OPENQASM_TO_ASIC_PIPELINE.md](OPENQASM_TO_ASIC_PIPELINE.md) for computation time vs qubit count.

**Pain points:**
- **File extension:** Both 2.0 and 3.0 often use `.qasm`. Version is determined by the first declaration line, not the extension. The UI does not explain this.
- **Syntax:** The editor has OpenQASM syntax highlighting (Monaco) but it’s generic (e.g. `include "stdgates.inc";` for 3.0 may not be highlighted as in the spec). No in-editor validation beyond the debounced API call.
- **Size limit:** Backend rejects QASM strings longer than 100,000 characters (400). The WUI does not show this limit; long paste may fail with a generic error.

---

## Step 4: Live validation

1. After pasting or loading, the app sends the content to `POST /api/validate_qasm` (debounced ~500 ms).
2. You see **Valid** (green) or **Invalid** with an error message and optional line number. Invalid lines can be highlighted in the editor (red margin/line).

**Pain points:**
- **OpenQASM 3.0 missing dependency:** If the backend does not have `qiskit-qasm3-import`, 3.0 source returns "Invalid QASM: parse or gate error" (or the full message if `QASIC_DEBUG=1`: "OpenQASM 3.0 parsing requires qiskit-qasm3-import. Install with: pip install qiskit-qasm3-import"). In production the short message does not tell the user to install the optional package.
- **Gate set:** ASIC supports only **H, X, Z, Rx, CNOT**. Other gates (e.g. T, S, Rz, U3) cause validation/circuit failure unless the backend uses decomposition (e.g. `decompose_to_asic=True` in the loader). The WUI does not explain the allowed gate set or that decomposition may be applied.
- **Line number:** When the API returns a line number, the editor highlights that line; if the API does not return a line, the user only sees the message.

---

## Step 5: Circuit Topology (EaC) tab (optional)

1. Switch the DAG tab to **Circuit Topology (EaC)**.
2. If the circuit is valid, the app calls `POST /api/circuit/topology` with the QASM string and displays a graph of qubit interactions (nodes = qubits or registers, edges = 2-qubit gates).

**Pain point:** Topology is only requested when the circuit is **valid**. If validation fails, this tab never shows a topology and there is no message like "Fix validation errors to see topology."

---

## Step 6: Choose circuit-driven pipeline (when QASM is present)

1. If the editor has QASM content, a **Circuit-driven pipeline** checkbox appears (default **checked** when you first add QASM in the session).
2. **Checked:** Full pipeline from circuit: **qasm → ASIC → routing → inverse → HEaC** (circuit-derived routing). Requires Celery/Redis for async; otherwise the backend runs it synchronously (can be slow or timeout).
3. **Unchecked:** Only **circuit → ASIC** (Algorithm-to-ASIC): parse → topology → geometry → superconducting extraction → custom ASIC manifest. No routing/inverse/HEaC in this path.

**Pain points:**
- **Async vs sync:** The WUI first tries `POST /api/run/pipeline/async`. If the server returns 503 (Celery/Redis not configured), the UI falls back to `POST /api/run/pipeline` (sync). Long runs can hit timeouts or appear to hang with no progress bar for sync.
- **No HEaC/routing options here:** Advanced options (e.g. `heac`, `routing_method`) exist in the API (`RunPipelineRequest`) but are not exposed in the Run Pipeline form. Users who want GDS/HEaC from the WUI have no checkbox or dropdown for it on this page.
- **Project (optional):** If projects exist, a "Project (optional)" dropdown is shown. Pipeline runs can be scoped to a project; the link from Home to "Create one" for projects is easy to miss for new users.

---

## Step 7: Run pipeline

1. Optionally set **Circuit name** (default "circuit"), **Backend** (Simulation / IBM hardware), **Fast** checkbox, and **Project** (if listed).
2. Click **Run pipeline**.
3. **If async (Celery available):** The UI shows a task ID, "In queue" / "Running…", and a **Live log** area (SSE from `/api/tasks/{task_id}/stream`). When the task completes, the result appears below; on failure, an error message is shown.
4. **If sync (no Celery):** No task ID; the button stays in a loading state until the API responds. Result or error appears when the request completes.

**Pain points:**
- **503 on async:** If Celery/Redis is not configured and the user has QASM + "Circuit-driven pipeline", the first request is async and may return 503; the UI then retries with sync. The message "Celery/Redis not configured" is only visible in the async response; the user may just see a generic error or a later sync error/timeout.
- **Result format:** Success shows a JSON result (e.g. `circuit_to_asic` with paths, or full pipeline result). There is no dedicated "Download GDS" or "View manifest" button on this page; for GDS you must use **View last results** / **Results** or the API (`GET /api/results/gds`).
- **Stop:** "Stop" cancels the Celery task; it is only shown when a task is pending or running. Sync runs cannot be cancelled from the UI.
- **Pipeline (DevOps) DAG:** The "Pipeline (DevOps)" tab shows the static pipeline DAG (routing, inverse, HEaC, GDS, etc.). Node status (pending/running/success/failed) is updated from the task stream when available; for sync runs there is no step-by-step status.

---

## Step 8: Interpret result and get artifacts

1. **Circuit-to-ASIC only:** The result includes paths for the custom ASIC manifest and extraction outputs (under the backend’s output directory). These are not directly downloadable from the WUI; use API or file system.
2. **Full pipeline with circuit:** Result may include routing and inverse design outputs. GDS is produced only if the pipeline runs with HEaC and GDS steps (e.g. `--heac --gds`); the Run Pipeline page does not expose this flag.
3. To **download GDS** or see latest run metadata: go to **View last results** (Home → "View last results") or **/results**, or call `GET /api/results/gds`.

**Pain points:**
- **No artifact list on Run Pipeline page:** The result JSON is shown but there is no "Download manifest" / "Download GDS" button. Users must know to go to Results or the API.
- **HEaC/GDS not default:** Getting a GDS from the WUI requires the full pipeline with HEaC enabled; the form does not expose this, so WUI-only users may not get a GDS without reading the docs or API.

---

## Summary: Pain points checklist

| # | Area | Pain point |
|---|------|------------|
| 1 | Discovery | No in-app guidance that "Run full pipeline" is the OpenQASM → ASIC path; no mention of OpenQASM 3.0 support. |
| 2 | Copy | UI says "OpenQASM 2" only; OpenQASM 3.0 is supported when backend has `qiskit-qasm3-import`. |
| 3 | Prerequisites | OpenQASM 3.0 requires optional backend dependency; error message is generic unless `QASIC_DEBUG=1`. |
| 4 | File/version | Version is by first line, not extension; UI does not explain. |
| 5 | Size limit | 100 KB QASM limit not shown in UI; long paste fails with opaque error. |
| 6 | Gate set | Allowed gates (H, X, Z, Rx, CNOT) and decomposition not explained in WUI. |
| 7 | Async vs sync | 503 + fallback to sync can confuse; sync long runs can timeout or hang with no progress. |
| 8 | Options | HEaC, routing method, and other API options not exposed on Run Pipeline form. |
| 9 | Artifacts | No "Download GDS" / "Download manifest" on Run Pipeline page; must use Results or API. |
| 10 | Circuit topology tab | No message when validation fails explaining why topology is not shown. |
| 11 | Computation time | No in-app guidance on computation time vs qubit count; see [OPENQASM_TO_ASIC_PIPELINE.md](OPENQASM_TO_ASIC_PIPELINE.md). |

---

## Quick reference: WUI flow

1. **Start stack:** `docker compose up -d --build` → open http://localhost  
2. **Navigate:** Home → **Run full pipeline**  
3. **Input:** Paste OpenQASM 2 or 3 (any qubit count) or upload `.qasm` file  
4. **Validate:** Wait for **Valid** (fix errors if **Invalid**)  
5. **Optional:** Switch to **Circuit Topology (EaC)** to see qubit interaction graph  
6. **Options:** Leave **Circuit-driven pipeline** checked for full pipeline, or uncheck for circuit-to-ASIC only  
7. **Run:** Click **Run pipeline**; wait for result or follow task log  
8. **Artifacts:** Use **View last results** / **/results** or `GET /api/results/gds` for GDS; backend output dir for manifest/artifacts  

For backend pipeline stages, code paths, and technical pain points (parsing, gates, topology, pulses, verification), see [OPENQASM_TO_ASIC_PIPELINE.md](OPENQASM_TO_ASIC_PIPELINE.md).
