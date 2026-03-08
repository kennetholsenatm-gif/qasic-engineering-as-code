# Engineering: Metasurface Routing and Inverse Design

Code supporting the **Holographic Metasurfaces and Cryogenic Architectures** whitepaper: QUBO-based qubit routing for the metasurface quantum bus, and ML inverse design for phase profiles. **No physical metamaterials required**—routing runs in simulation or on real IBM Quantum; inverse design runs on CPU/GPU.

**Ready-to-run:** (1) `routing_qubo_qaoa.py` — QUBO routing with QAOA/NumPy; (2) `metasurface_inverse_net.py` — PyTorch inverse design; (3) `run_pipeline.py` — run routing then inverse design in one command; (4) `viz_routing_phase.py` — summarize routing JSON and phase array; (5) `run_protocol_on_ibm.py` — run ASIC protocol (teleport, Bell, etc.) on IBM Quantum or simulator; single job, minimal cost. Install deps with `pip install -r engineering/requirements-engineering.txt`, then run as below.

## Overview

| Script / module | Purpose |
|----------------|--------|
| **`routing_qubo_qaoa.py`** | Map **logical qubits** (e.g. Alice, Bob, Message) to **physical nodes** (metasurface interaction zones). Formulated as a QUBO: minimize total “interaction distance” subject to 1:1 assignment. Solves with QAOA when Qiskit is available, with a classical fallback. Use `--fast` or `--maxiter`/`--reps` for affordable hardware runs (see "Engineering as Code on IBM Quantum"). |
| **`metasurface_inverse_net.py`** | **Inverse design**: input = desired quantum topology / beam-steering features → output = phase shifts per meta-atom. Default [0, 2π]; optional `--phase-band pi` (or `lo,hi`) constrains to narrow band around π for Cryo-CMOS thermal budget. PyTorch MLP; trainable to match target phase profiles or downstream EM/quantum metrics. |
| **`run_pipeline.py`** | Run routing (sim or `--hardware`) then inverse design; writes `*_routing.json`, `*_inverse.json`, `*_inverse_phases.npy`. No physical metasurface needed. |
| **`viz_routing_phase.py`** | Load routing JSON and optionally inverse JSON / phase .npy; print mapping, objective, phase stats, optional `--histogram`. |
| **`viz_topology.py`** | Draw topology graph (matplotlib): nodes on a circle, edges; optional logical→physical labels from routing JSON. Use `--topology` (linear_chain, star, repeater_chain), `--qubits`, `-o out.png`. Requires matplotlib. |
| **`run_protocol_on_ibm.py`** | Run ASIC protocol (teleport, Bell, commitment, thief) on IBM Quantum or simulator. Single circuit, one Sampler job; minimal QPU time (&lt;1 min). |
| **`squid_spectrum_scqubits.py`** | Optional. rf-SQUID/Fluxonium spectrum and sweet spots via **scqubits**: flux sweep, eigenvalue diagonalization. Requires `pip install scqubits`. |
| **`open_system_qutip.py`** | Optional. Lindblad master equation demo: qubit relaxation and dephasing (TLS-like). Requires `pip install qutip`. |
| **`forward_prediction_net.py`** | Stub: config vector → S-parameters / transmission (FEM surrogate). Use `--synthetic` for random-data training stub; in production train on FEM/FDTD data. |
| **`superscreen_demo.py`** | Optional. Minimal SuperScreen run: 2D London equation, ring device, Meissner screening. Requires `pip install superscreen`. See [../docs/superscreen_integration.md](../docs/superscreen_integration.md). |
| **`thermodynamic_validator.py`** | **Graph-Theoretic whitepaper:** Validate phase profiles for π-radian baseline (sub-radian band) and 18 nW/cell Cryo-CMOS proxy. Input: .npy or inverse JSON. Output: report or JSON. |
| **`phase_synthesis_report.py`** | Phase stats + thermodynamic validation in one report. Input: inverse JSON or .npy; optional `--json`. |
| **`benchmark_mlp_vs_gnn.py`** | Compare MLP vs GNN inverse design: phase stats, thermodynamic compliance, optional MSE to π target. Use `--routing-result` for both models; `-o` JSON, `--table` for summary. |
| **`graph_from_geometry.py`** | Build physics-aligned graphs for the GNN: 2D grid or coupling-matrix topology. `--grid NX,NY` or `--routing FILE`; optional `-o BASE` to save tensors. |
| **`heac/`** | **HEaC (open-source, Meep):** `meep_unit_cell_sweep.py` (meta-atom library), `phase_to_dimension.py` (φ→d), `phases_to_geometry.py` (phases.npy→manifest), `manifest_to_gds.py` (optional gdsfactory; `--pdk-config` for PDK), `run_drc_klayout.py`, `run_lvs_klayout.py` (DRC/LVS or mock). See [Hardware-Engineering-as-Code](#hardware-engineering-as-code-open-source-meep) below. |
| **`calibration/`** | **Digital twin:** Ingest quantum telemetry (T1/T2 per qubit), Bayesian update of decoherence rates, output `decoherence_from_calibration.json` for routing/simulation. See [../docs/CALIBRATION_DIGITAL_TWIN.md](../docs/CALIBRATION_DIGITAL_TWIN.md). |
| **`thermal_stages.py`** | Lumped thermal report (10 mK / 4 K / 50 K) from routing + phases. Use `run_pipeline.py --thermal`. |
| **`parasitic_extraction.py`** | Layout-aware decoherence from geometry manifest (and routing). Use `run_pipeline.py --heac --parasitic`. |

## Relation to the rest of the repo

- **Quantum ASIC** (`../asic/`) defines the *logical* topology and gate set (e.g. linear chain 0–1–2, H/X/Z/CNOT). The **routing** script decides *where* those logical qubits sit on the physical metasurface (which zone is “Alice”, which “Bob”, etc.) so that required interactions (e.g. CNOT(0,1), CNOT(1,2)) have minimal cost (e.g. distance).
- The **inverse net** takes high-level targets (e.g. “Bell pair between zone A and B”, steering angle) and outputs the **phase profile** for the active matrix, which the physical metasurface then implements.

So: **protocol layer** (ASIC) → **routing** (which logical qubit on which node) → **inverse design** (phase shifts per meta-atom).

### Hardware CI

When you push or open a PR that touches `protocols/`, `asic/`, `engineering/`, `apps/`, or `state/`, the **Hardware CI** workflow (`.github/workflows/hardware-ci.yml`) runs unit tests, then the pipeline with `--heac --fast`, then the thermodynamic validator. On PRs, it optionally runs `engineering/ci_gds_diff.py` to compare the new manifest (and phase summary) to a baseline in `engineering/ci_baseline/`. To get diff reports, add `ci_result_geometry_manifest.json` (and optionally `ci_result_inverse_phases.npy`) to `engineering/ci_baseline/` and update them on merge to main.

### Engineering-as-Code stack

The full stack described in the whitepapers is: **Protocol** (ASIC + state-vector sim) → **Routing** (QUBO/Qiskit QAOA) → **Inverse design** (PyTorch DNN). Optional/future layers: **scqubits** (rf-SQUID Hamiltonian, sweet spots), **SuperScreen** (2D London equation, Meissner/inductance), **QuTiP** (open systems, TLS decoherence), **forward CNN** (FEM surrogate for S-parameters). See [Engineering as Code: Distributed Computational Roadmap](../docs/Engineering_as_Code_Distributed_Computational_Roadmap.tex) and [Computational Materials Science and Simulation Architectures](../docs/Computational_Materials_Science_Cryogenic_Quantum_Metamaterials.tex) (LaTeX; build PDFs with `.\docs\build_pdfs.ps1`).

## Setup

From repo root (recommended: use a venv and Python 3.10+ for Qiskit 2.x):

```bash
pip install -r engineering/requirements-engineering.txt
```
This installs `numpy`, `qiskit`, `qiskit-optimization`, and `torch`. To run only one workload, install the subset you need (see below).

Or install only what you need:

- Routing (QUBO + QAOA or classical): `pip install qiskit qiskit-optimization hashable-list ordered-set`. For real hardware add `qiskit-ibm-runtime` and set env **`IBM_QUANTUM_TOKEN`** (same as BQTC/QRNG). Optional: `--token YOUR_TOKEN` or save via `QiskitRuntimeService.save_account(channel='ibm_quantum_platform', token='...')`. API: `QuadraticProgram`, `MinimumEigenOptimizer`, `QAOA` / `NumPyMinimumEigensolver` from `qiskit_optimization`; `StatevectorSampler` from `qiskit.primitives`; `COBYLA` from `qiskit_optimization.optimizers`; `result.x`, `result.fval` from `optimizer.solve(qp)`.
- Protocol on IBM: `pip install qiskit`. For `--hardware`, add `qiskit-ibm-runtime` and set **`IBM_QUANTUM_TOKEN`**. Run from repo root so `asic` is importable.
- Inverse design: `pip install torch`.

## Running

**Workload 1 — QUBO routing (QAOA or classical):**
```bash
cd engineering
python routing_qubo_qaoa.py              # simulation (StatevectorSampler)
python routing_qubo_qaoa.py --topology star --qubits 4 --hub 0 -o star_routing.json   # named topology
python routing_qubo_qaoa.py --hardware   # real IBM Quantum hardware (requires qiskit-ibm-runtime + credentials)
python routing_qubo_qaoa.py --hardware --fast   # budget preset: fewer iters/reps, under 5 min QPU time
python routing_qubo_qaoa.py --hardware --maxiter 25 --reps 1   # custom budget
python routing_qubo_qaoa.py --hardware --backend ibm_brisbane  # specific backend
python routing_qubo_qaoa.py --hardware -o result.json          # write result to JSON file
```
Or from repo root: `python engineering/routing_qubo_qaoa.py`. Topology choices: `linear`, `linear_chain`, `star`, `repeater`, `repeater_chain`; see [../docs/TOPOLOGY_BUILDER.md](../docs/TOPOLOGY_BUILDER.md).

**Workload 1a — Topology visualizer:**
```bash
python engineering/viz_topology.py --topology star --qubits 4 -o star.png
python engineering/viz_topology.py star_routing.json -o star.png   # with mapping from routing JSON
```
Requires matplotlib. See [../docs/TOPOLOGY_BUILDER.md](../docs/TOPOLOGY_BUILDER.md).

**Workload 1b — Protocol on IBM Quantum (single job, &lt;1 min):**
```bash
python engineering/run_protocol_on_ibm.py                      # simulation, teleport
python engineering/run_protocol_on_ibm.py --protocol bell        # Bell pair
python engineering/run_protocol_on_ibm.py --hardware           # real IBM backend (qiskit-ibm-runtime + IBM_QUANTUM_TOKEN)
python engineering/run_protocol_on_ibm.py --hardware -o protocol_result.json
```
Run from repo root so `asic` is importable.

**Workload 2 — Metasurface inverse net (forward pass):**
```bash
cd engineering
python metasurface_inverse_net.py                    # CPU, random topology
python metasurface_inverse_net.py --device cuda     # run on GPU
python metasurface_inverse_net.py --device auto -o inverse_result.json   # auto device, write JSON + phases .npy
python metasurface_inverse_net.py --routing-result result.json -o inverse_result.json  # use routing JSON as topology input
python metasurface_inverse_net.py --phase-band pi -o cryo_result.json   # constrain phases to pi±0.14 rad (Cryo-CMOS)
```
Or from repo root: `python engineering/metasurface_inverse_net.py`

**Full pipeline (routing → inverse design, no physical metasurface):**

The pipeline writes all outputs under the **`engineering/`** directory. With default base name `pipeline_result`, it creates `engineering/pipeline_result_routing.json`, `engineering/pipeline_result_inverse.json`, and `engineering/pipeline_result_inverse_phases.npy`. Use `-o BASE` to change the base (e.g. `-o my_run` → `my_run_routing.json`, etc., still under `engineering/`).

- **Routing options:** `--routing-method qaoa` (default) or `--routing-method rl` for RL-based local-search routing. For decoherence-aware routing use `python engineering/routing_qubo_qaoa.py --use-qutip-decoherence` (requires `qutip`).
- **Inverse design:** `--model mlp` (default) or `--model gnn` for graph neural network (requires `--routing-result`).
- **SuperScreen:** `--with-superscreen` to compute inductance from routing topology (optional; requires `superscreen`).

```bash
pip install -r engineering/requirements-engineering.txt
python engineering/run_pipeline.py
python engineering/run_pipeline.py --routing-method rl --model gnn   # RL routing + GNN inverse
python engineering/viz_routing_phase.py engineering/pipeline_result_routing.json --inverse engineering/pipeline_result_inverse.json --histogram
```

**Viz paths:** Paths are relative to your current working directory. When you run from repo root, use `engineering/...` for pipeline outputs. With `--inverse`, the phase array path from the JSON is resolved relative to the inverse JSON file's directory.

**Quick check (routing + inverse only):**
```bash
pip install -r engineering/requirements-engineering.txt
python engineering/routing_qubo_qaoa.py
python engineering/metasurface_inverse_net.py
```

## Routing QUBO details

- **Variables:** `x_{i,j}` binary: logical qubit `i` is at physical node `j`.
- **Constraints:** Each logical qubit at exactly one node; each node has exactly one logical qubit (permutation).
- **Objective:** Sum over pairs (i1, i2) that must interact of `distance(j1, j2)` when logical i1 is at j1 and i2 at j2. Default “interaction” is a linear chain (0–1, 1–2) to match the Quantum ASIC teleport topology.
- **Solver:** QAOA (quantum) with `StatevectorSampler`, or `NumPyMinimumEigensolver` (exact classical) from `qiskit_optimization`.

## Inverse net details

- **Input:** Vector of size `target_topology_features` (e.g. 10): desired coupling graph, steering angles, or from `--routing-result` (routing JSON).
- **Output:** `num_meta_atoms` phases in [0, 2π] by default, or in a narrow band when `--phase-band` is set. With `-o FILE`: writes `FILE` (JSON with device, phase stats, path to phase array) and `FILE` base + `_phases.npy` (NumPy array).
- **Phase band:** `--phase-band pi` constrains phases to π ± 0.14 rad (≈ 3.03–3.28 rad) to match the whitepaper’s Cryo-CMOS 18 nW/cell constraint; `--phase-band lo,hi` uses custom bounds in radians.
- **Device:** `--device auto|cpu|cuda|mps` (auto = GPU if available).
- **Training:** Stub uses MSE to a target phase profile; in practice, loss can be EM-based or fidelity-based.

### Graph-Theoretic Inverse Design (whitepaper-driven tools)

The [Graph-Theoretic Inverse Design](../docs/Graph_Theoretic_Inverse_Design_GNN_Metasurfaces.tex) whitepaper motivates these utilities:

**Thermodynamic validation and phase reports:**
```bash
python engineering/thermodynamic_validator.py pipeline_result_inverse.json
python engineering/thermodynamic_validator.py engineering/pipeline_result_inverse_phases.npy -j   # JSON output
python engineering/phase_synthesis_report.py engineering/pipeline_result_inverse.json
python engineering/phase_synthesis_report.py engineering/pipeline_result_inverse_phases.npy --json
```

**MLP vs GNN benchmark** (same routing input, compare phase stats and π-band compliance):
```bash
python engineering/benchmark_mlp_vs_gnn.py --routing-result engineering/pipeline_result_routing.json --table -o benchmark.json
python engineering/benchmark_mlp_vs_gnn.py --routing-result engineering/pipeline_result_routing.json --phase-band pi --meta-atoms 500
```

**Physics-aligned graph construction** (for GNN from grid or routing):
```bash
python engineering/graph_from_geometry.py --grid 10,10 -o engineering/grid_10x10
python engineering/graph_from_geometry.py --routing engineering/pipeline_result_routing.json
```

### Hardware-Engineering-as-Code (open-source, Meep)

The [Automated HEaC whitepaper](../docs/Automated_HEaC_Deep_Cryogenic_Quantum_ASICs.tex) describes compiling `phases.npy` and `routing.json` into manufacturing-ready geometry. The open-source stack uses **Meep** (FDTD) for EM validation and optional **gdsfactory** for GDSII. See [HEaC open-source (Meep)](../docs/HEaC_opensource_Meep.md) for the tool chain summary.

**1. Build meta-atom library** (dimension → transmission phase). With Meep: real unit-cell sweep; without: synthetic formula.
```bash
python engineering/heac/meep_unit_cell_sweep.py -o engineering/meta_atom_library.json --points 21
python engineering/heac/meep_unit_cell_sweep.py --no-meep -o engineering/meta_atom_library.json   # synthetic
```

**2. Phase-to-dimension interpolator** (load library, query dimension for a given phase):
```bash
python engineering/heac/phase_to_dimension.py engineering/meta_atom_library.json --table
```

**3. Phases.npy → geometry manifest** (compile pipeline phase array to cell list for GDS/CadQuery):
```bash
python engineering/heac/phases_to_geometry.py engineering/pipeline_result_inverse_phases.npy --library engineering/meta_atom_library.json -o engineering/geometry_manifest.json
```

**4. Optional: manifest → GDSII** (requires `gdsfactory`):
```bash
python engineering/heac/manifest_to_gds.py engineering/geometry_manifest.json -o engineering/metasurface.gds
```

**Pipeline integration:** Run routing, inverse design, and HEaC manifest in one command:
```bash
python engineering/run_pipeline.py --heac
```
If `meta_atom_library.json` is missing, a synthetic library is generated automatically. Use `--heac-library PATH` to supply a custom library. For GDS export and DRC/LVS, use `--heac --gds` (writes `.gds`), `--drc` (run DRC; mock if KLayout not on PATH), and `--lvs` (layout vs schematic; mock if KLayout not installed). Use `--pdk` to apply `heac/pdk_config.yaml` (layer numbers, min width/spacing).

**Optional dependencies:** `scipy` (interpolator), `pymeep` (Meep FDTD for library sweep), `gdsfactory` (GDS export). See [engineering/requirements-engineering.txt](requirements-engineering.txt).

## Output formats (JSON schema)

These shapes are consumed by `viz_routing_phase.py` and by chaining (e.g. `--routing-result`). Keeping keys consistent avoids breakage.

**Routing JSON** (from `routing_qubo_qaoa.py -o`):
- `num_logical_qubits`, `num_physical_nodes` (int)
- `solver` (str), `objective_value` (float or null), `backend` (str or null)
- `mapping`: list of `{"logical": int, "physical": int}`
- `timestamp` (str, ISO UTC)

**Inverse design JSON** (from `metasurface_inverse_net.py -o`):
- `device`, `num_meta_atoms`, `target_topology_features`
- `phase_min`, `phase_max`, `phase_mean` (float; viz uses these for display)
- `phase_array_path` (str, basename of the .npy file; viz resolves relative to the JSON's directory)
- `routing_result` (optional), `timestamp`

## Engineering as Code on IBM Quantum (affordable, &lt;5 min)

IBM bills **computational (QPU) time** per second; queue time is separate. To keep runs affordable (under 5 minutes of QPU time):

1. **QUBO routing (QAOA):** Use `--hardware --fast` for a budget preset (~20 COBYLA iters, 1 QAOA layer, ~20k shots, est. QPU time ~1–2 s). Or set explicitly: `--maxiter 25 --reps 1`. Default `--maxiter 100 --reps 2` uses ~100k shots (~5 s); use lower values for cheaper runs.
2. **Protocol on hardware:** `run_protocol_on_ibm.py --hardware` runs one 3-qubit circuit (e.g. teleportation), single job, 1024 shots by default — well under 1 minute QPU time.

Set **`IBM_QUANTUM_TOKEN`** (or use `--token`) for real hardware. See [IBM Quantum pricing](https://www.ibm.com/quantum/pricing) for plans.

## Rough quantum computation time (routing QAOA)

For the **default 3×3 routing problem** (3 logical qubits, 3 physical nodes, `reps=2`, COBYLA `maxiter=100`):

| Resource | Estimate |
|----------|----------|
| **Qubits** | 9 (one per binary variable in the QUBO) |
| **Circuit evaluations** | ~100 (one per COBYLA iteration) |
| **Shots per evaluation** | 1024 (if run on real hardware; StatevectorSampler uses exact expectation, no shots) |
| **Total shots on real HW** | ~100 × 1024 ≈ **100k shots** |
| **Simulator (StatevectorSampler)** | Typically **a few seconds** to ~30 s (exact statevector, no shot noise) |
| **Real quantum hardware** | Raw execution ~**5–30 s** at 50 μs/shot; **queue time** on shared cloud usually dominates (minutes to hours) |

**Budget preset (`--fast`):** `--maxiter 20 --reps 1` → ~20 circuit evals, ~20k shots, est. QPU time ~1–2 s. Use for affordable runs under 5 min QPU time.

Scaling: doubling logical/physical nodes (e.g. 6×6) gives 36 qubits and a much larger circuit; simulator time grows quickly (statevector 2^36), and real-device queue and decoherence become limiting. Use `estimate_quantum_resources()` in `routing_qubo_qaoa.py` for custom problem sizes.

## Reference

- Whitepaper: `../docs/WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.md`
- PDF: *Holographic Metasurfaces and Cryogenic Architectures for Scalable Quantum Computing and Satellite Communications*
