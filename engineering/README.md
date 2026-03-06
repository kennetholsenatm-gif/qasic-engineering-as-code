# Engineering: Metasurface Routing and Inverse Design

Code supporting the **Holographic Metasurfaces and Cryogenic Architectures** whitepaper: QUBO-based qubit routing for the metasurface quantum bus, and ML inverse design for phase profiles.

**Ready-to-run workloads:** (1) `routing_qubo_qaoa.py` — QUBO routing with QAOA/NumPy; (2) `metasurface_inverse_net.py` — PyTorch inverse design. Install deps with `pip install -r engineering/requirements-engineering.txt`, then run the two scripts as below.

## Overview

| Script / module | Purpose |
|----------------|--------|
| **`routing_qubo_qaoa.py`** | Map **logical qubits** (e.g. Alice, Bob, Message) to **physical nodes** (metasurface interaction zones). Formulated as a QUBO: minimize total “interaction distance” subject to 1:1 assignment. Solves with QAOA when Qiskit is available, with a classical fallback. |
| **`metasurface_inverse_net.py`** | **Inverse design**: input = desired quantum topology / beam-steering features → output = phase shifts (0–2π) per meta-atom. PyTorch MLP; trainable to match target phase profiles or downstream EM/quantum metrics. |

## Relation to the rest of the repo

- **Quantum ASIC** (`../asic/`) defines the *logical* topology and gate set (e.g. linear chain 0–1–2, H/X/Z/CNOT). The **routing** script decides *where* those logical qubits sit on the physical metasurface (which zone is “Alice”, which “Bob”, etc.) so that required interactions (e.g. CNOT(0,1), CNOT(1,2)) have minimal cost (e.g. distance).
- The **inverse net** takes high-level targets (e.g. “Bell pair between zone A and B”, steering angle) and outputs the **phase profile** for the active matrix, which the physical metasurface then implements.

So: **protocol layer** (ASIC) → **routing** (which logical qubit on which node) → **inverse design** (phase shifts per meta-atom).

## Setup

From repo root (recommended: use a venv and Python 3.10+ for Qiskit 2.x):

```bash
pip install -r engineering/requirements-engineering.txt
```
This installs `numpy`, `qiskit`, `qiskit-optimization`, and `torch`. To run only one workload, install the subset you need (see below).

Or install only what you need:

- Routing (QUBO + QAOA or classical): `pip install qiskit qiskit-optimization hashable-list ordered-set`. For real hardware add `qiskit-ibm-runtime` and set env **`IBM_QUANTUM_TOKEN`** (same as BQTC/QRNG). Optional: `--token YOUR_TOKEN` or save via `QiskitRuntimeService.save_account(channel='ibm_quantum_platform', token='...')`. API: `QuadraticProgram`, `MinimumEigenOptimizer`, `QAOA` / `NumPyMinimumEigensolver` from `qiskit_optimization`; `StatevectorSampler` from `qiskit.primitives`; `COBYLA` from `qiskit_optimization.optimizers`; `result.x`, `result.fval` from `optimizer.solve(qp)`.
- Inverse design: `pip install torch`.

## Running

**Workload 1 — QUBO routing (QAOA or classical):**
```bash
cd engineering
python routing_qubo_qaoa.py              # simulation (StatevectorSampler)
python routing_qubo_qaoa.py --hardware   # real IBM Quantum hardware (requires qiskit-ibm-runtime + credentials)
python routing_qubo_qaoa.py --hardware --backend ibm_brisbane  # specific backend
python routing_qubo_qaoa.py --hardware -o result.json          # write result to JSON file
```
Or from repo root: `python engineering/routing_qubo_qaoa.py`

**Workload 2 — Metasurface inverse net (forward pass):**
```bash
cd engineering
python metasurface_inverse_net.py                    # CPU, random topology
python metasurface_inverse_net.py --device cuda     # run on GPU
python metasurface_inverse_net.py --device auto -o inverse_result.json   # auto device, write JSON + phases .npy
python metasurface_inverse_net.py --routing-result result.json -o inverse_result.json  # use routing JSON as topology input
```
Or from repo root: `python engineering/metasurface_inverse_net.py`

**Quick check (both workloads):**
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
- **Output:** `num_meta_atoms` phases in [0, 2π] (e.g. 1000 meta-atoms). With `-o FILE`: writes `FILE` (JSON with device, phase stats, path to phase array) and `FILE` base + `_phases.npy` (NumPy array).
- **Device:** `--device auto|cpu|cuda|mps` (auto = GPU if available).
- **Training:** Stub uses MSE to a target phase profile; in practice, loss can be EM-based or fidelity-based.

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

Scaling: doubling logical/physical nodes (e.g. 6×6) gives 36 qubits and a much larger circuit; simulator time grows quickly (statevector 2^36), and real-device queue and decoherence become limiting. Use `estimate_quantum_resources()` in `routing_qubo_qaoa.py` for custom problem sizes.

## Reference

- Whitepaper: `../docs/WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.md`
- PDF: *Holographic Metasurfaces and Cryogenic Architectures for Scalable Quantum Computing and Satellite Communications*
