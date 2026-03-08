# Next Steps: Maturity Roadmap by Engineering Domain

This document captures suggested next steps to mature the qasic-engineering-as-code framework beyond the current production-oriented baseline (PDK/DRC/LVS, pulse compiler, thermal/parasitics, Hardware CI, digital-twin calibration). Items are grouped by engineering domain and linked to existing code paths.

---

## 1. Tapeout Readiness & LVS/Extraction Refinement

The baseline [engineering/heac/run_drc_klayout.py](../engineering/heac/run_drc_klayout.py) and [engineering/heac/run_lvs_klayout.py](../engineering/heac/run_lvs_klayout.py) provide DRC and LVS (schematic vs layout). The following refinements target **superconducting** tapeouts and **design-for-test**.

### 1.1 Superconducting Extraction (Kinetic Inductance)

**Goal:** Standard LVS is CMOS-oriented. Superconducting circuits require extraction of **kinetic inductance** of traces and **Josephson Junction (JJ) nonlinear inductance** from GDS geometries.

**Implementation directions:**

- Implement a **custom extraction routine** (or wrapper) that:
  - Reads GDS or geometry manifest (e.g. from [engineering/heac/manifest_to_gds.py](../engineering/heac/manifest_to_gds.py) / [phases_to_geometry.py](../engineering/heac/phases_to_geometry.py)).
  - Computes trace kinetic inductance (e.g. length × inductance per unit length from layer/width).
  - Identifies JJ regions (e.g. by layer or cell type) and computes JJ inductance from critical current / geometry.
- **Integration options:**
  - **FastHenry** (or similar) wrapper for 3D inductance extraction; output format consumable by [engineering/decoherence_rates.py](../engineering/decoherence_rates.py) or a new `engineering/superconducting_extraction.py`.
  - **Custom LVS rule deck** (KLayout DRC/LVS script) that outputs a netlist + parasitic summary (L, C) instead of only connectivity.
- **Output:** Same decoherence/parasitic contract as [engineering/parasitic_extraction.py](../engineering/parasitic_extraction.py) (e.g. per-node or per-edge L/C), or a new `*_kinetic_inductance.json` used by routing or Hamiltonian construction.

**Relevant files:** [engineering/heac/](../engineering/heac/), [engineering/parasitic_extraction.py](../engineering/parasitic_extraction.py), [engineering/decoherence_rates.py](../engineering/decoherence_rates.py).

---

### 1.2 Automated DFT & Padframes

**Goal:** The HEaC module generates core geometry; extend it to **automate padframes, alignment marks, and witness structures** (standalone resonators, single JJs for fab characterization).

**Implementation directions:**

- **Padframes:** Script generation of bond pads and routing from core metasurface boundary to pad ring (layer map from [engineering/heac/pdk_config.yaml](../engineering/heac/pdk_config.yaml)); output remains GDS or extended geometry manifest.
- **Alignment marks:** Add standard marks (e.g. crosses, frames) at chip corners/edges via a small module (e.g. `engineering/heac/dft_structures.py`) that the main manifest→GDS path can call.
- **Witness structures:** Generate separate GDS cells or a “witness” layer with:
  - Standalone resonators (for linewidth / Q extraction).
  - Single JJs or small JJ chains (for Ic, Rn characterization).
- **Integration:** Optional `--dft` flag in [engineering/run_pipeline.py](../engineering/run_pipeline.py) that, after HEaC manifest→GDS, runs the DFT script and merges or appends padframe + witnesses to the layout.

**Relevant files:** [engineering/heac/manifest_to_gds.py](../engineering/heac/manifest_to_gds.py), [engineering/heac/phases_to_geometry.py](../engineering/heac/phases_to_geometry.py), [engineering/run_pipeline.py](../engineering/run_pipeline.py).

---

### 1.3 Process Variation (Monte Carlo) Sweeps

**Goal:** Use codified layout and geometry to run **process variation sweeps**: perturb JJ dimensions or dielectric thicknesses in the manifest, re-run parasitic/superconducting extraction, and predict **spread of qubit frequencies** for wafer yield estimation.

**Implementation directions:**

- **Perturbation layer:** From a nominal geometry manifest, generate N variants (e.g. dimension ±Δ, or Gaussian draws from a process distribution); write `manifest_variant_0.json`, … or a single batch description.
- **Loop:** For each variant, run [engineering/parasitic_extraction.py](../engineering/parasitic_extraction.py) (and, when available, superconducting extraction); optionally re-run thermal or decoherence update.
- **Metric:** Map extracted L/C (or qubit frequency proxy) to a simple Hamiltonian or resonance model; collect statistics (mean, std, yield at spec).
- **Entry point:** New script e.g. `engineering/process_variation_sweep.py` (CLI: nominal manifest, number of samples, parameter ranges); optional integration in Hardware CI as a separate job (long-running).

**Relevant files:** [engineering/heac/phases_to_geometry.py](../engineering/heac/phases_to_geometry.py), [engineering/parasitic_extraction.py](../engineering/parasitic_extraction.py), [asic/topology.py](../asic/topology.py) (if Hamiltonian is updated from extraction).

---

## 2. Control Electronics & Hardware-in-the-Loop (HIL)

The [pulse/](../pulse/) directory ([openpulse_backend.py](../pulse/openpulse_backend.py), [pseudo_schedule.py](../pulse/pseudo_schedule.py)) maps circuits to microwave pulse envelopes. Next steps target **real control hardware** and **HIL in CI**.

### 2.1 Target Specific FPGA/AWG Backends

**Goal:** Extend the pulse compiler to emit **bitstreams or waveform configs** for real control hardware (e.g. Xilinx RFSoC via **QICK**, or Zurich Instruments).

**Implementation directions:**

- **QICK (Quantum Instrumentation Control Kit):** Add a backend (e.g. [pulse/qick_export.py](../pulse/) or under `pulse/backends/`) that:
  - Consumes the same schedule representation produced by [pulse/compiler.py](../pulse/compiler.py) (OpenPulse or pseudo-schedule dict).
  - Outputs QICK-compatible Python or config (waveform definitions, timing, channel map).
- **Zurich Instruments:** Similarly, a backend that maps schedule instructions to ZI API calls or configuration files.
- **API:** Keep [pulse/compiler.py](../pulse/compiler.py) as the single entry; add `--backend qick` or `--backend zürich` to [pulse/compile_cli.py](../pulse/compile_cli.py) (or `python -m pulse`) to select the exporter.

**Relevant files:** [pulse/compiler.py](../pulse/compiler.py), [pulse/openpulse_backend.py](../pulse/openpulse_backend.py), [pulse/pseudo_schedule.py](../pulse/pseudo_schedule.py), [docs/PULSE_CONTROL.md](PULSE_CONTROL.md).

---

### 2.2 Hardware-in-the-Loop CI

**Goal:** In addition to GDS/manifest diffs, have CI **compile a pulse schedule** and run a **simulated calibration loop** (digital twin) to verify that proposed changes do not break **physical control fidelity**.

**Implementation directions:**

- **Workflow extension** in [.github/workflows/hardware-ci.yml](../.github/workflows/hardware-ci.yml):
  - After pipeline + thermodynamic validation, run: compile a fixed ASIC circuit (e.g. teleport) to schedule via `python -m pulse --circuit teleport -o ci_schedule.json`.
  - Run [engineering/calibration/run_calibration_cycle.py](../engineering/calibration/run_calibration_cycle.py) with **synthetic telemetry** (e.g. a fixture JSON with T1/T2 per qubit), producing `decoherence_from_calibration.json`.
  - Optionally run routing with `--decoherence-file ci_decoherence.json` and assert that the pipeline completes and key outputs (e.g. mapping, phase count) remain within bounds.
- **Assertions:** Add a small script or pytest step that checks: schedule has expected instruction count; calibration cycle exits 0; routing with calibration decoherence produces a valid mapping. This gives “HIL-style” confidence that control and calibration paths still work together.

**Relevant files:** [.github/workflows/hardware-ci.yml](../.github/workflows/hardware-ci.yml), [pulse/](../pulse/), [engineering/calibration/](../engineering/calibration/), [engineering/routing_qubo_qaoa.py](../engineering/routing_qubo_qaoa.py).

---

## 3. Cryogenic & Thermodynamic Integration

[engineering/thermodynamic_validator.py](../engineering/thermodynamic_validator.py) and [engineering/thermal_stages.py](../engineering/thermal_stages.py) model the dilution refrigerator environment. Next steps **close the loop** with open-quantum-system simulations and classical interface heat.

### 3.1 Closed-Loop Noise Modeling

**Goal:** Feed **thermodynamic model outputs** (e.g. per-node or localized temperatures) directly into **open-quantum-system** simulations so that hot spots (e.g. high-dissipation readout near a qubit) **automatically degrade T₁/T₂** in the QuTiP model.

**Implementation directions:**

- **Thermal → decoherence mapping:** Extend [engineering/thermal_stages.py](../engineering/thermal_stages.py) (or add a small `thermal_to_decoherence.py`) to output a **per-node or per-qubit** temperature or “thermal risk” score. Map that to γ₁, γ₂ (e.g. T₁ ∝ 1/T_bath, or an empirical curve).
- **Consumers:** [engineering/decoherence_rates.py](../engineering/decoherence_rates.py) already accepts a file of per-node `gamma1`/`gamma2`. Feed the thermal-derived file into it. Similarly, [engineering/open_system_qutip.py](../engineering/open_system_qutip.py) takes `gamma1`, `gamma2`; drive these from the thermal report (e.g. by loading `*_thermal_report.json` and a mapping table).
- **Router feedback:** If the router places a high-dissipation readout line near a qubit, the thermal stage should flag a localized temperature bump; that node’s T₁/T₂ in the decoherence file increase (worse), so routing or placement can penalize that assignment in a future run.

**Relevant files:** [engineering/thermal_stages.py](../engineering/thermal_stages.py), [engineering/decoherence_rates.py](../engineering/decoherence_rates.py), [engineering/open_system_qutip.py](../engineering/open_system_qutip.py), [engineering/routing_qubo_qaoa.py](../engineering/routing_qubo_qaoa.py) (decoherence penalty).

---

### 3.2 Cryo-CMOS / Classical Interface

**Goal:** If the ASIC uses **deep cryogenic classical logic** (e.g. SFQ or Cryo-CMOS) for control/routing, add **heat dissipation models** for that logic and its impact on the **quantum data plane**.

**Implementation directions:**

- **Power model:** From [engineering/routing_rl.py](../engineering/routing_rl.py) or the classical “routing” decision (e.g. which control lines are active), estimate power per node or per control line. Feed this into the same thermal stage (e.g. [engineering/thermal_stages.py](../engineering/thermal_stages.py)) as an extra power term (e.g. “classical routing power” per zone).
- **Thermal report:** Extend the thermal report to include a breakdown: “quantum cell power” vs “classical interface power” so that design can balance readout/control density against qubit coherence.
- **Documentation:** In [docs/THERMAL_AND_PARASITICS.md](THERMAL_AND_PARASITICS.md), describe the Cryo-CMOS/classical heat model and how it couples to the existing phase-based and routing-based power proxy.

**Relevant files:** [engineering/thermal_stages.py](../engineering/thermal_stages.py), [engineering/routing_rl.py](../engineering/routing_rl.py), [engineering/thermodynamic_validator.py](../engineering/thermodynamic_validator.py), [docs/THERMAL_AND_PARASITICS.md](THERMAL_AND_PARASITICS.md).

---

## 4. Interoperability and Standardization

Making the stack consumable by the broader quantum software ecosystem and hardening the GDS–EM pipeline.

### 4.1 OpenQASM 3.0 / QIR Integration

**Goal:** Allow [asic/circuit.py](../asic/circuit.py) and [pulse/compiler.py](../pulse/compiler.py) to **ingest OpenQASM 3.0** or **LLVM-based QIR** (Quantum Intermediate Representation) so that circuits defined in standard formats can be compiled to the ASIC gate set and then to pulses.

**Implementation directions:**

- **OpenQASM 3.0:** Add a parser or use an existing library (e.g. `qiskit.qasm2`/`qasm3`) to load a `.qasm` file and produce a list of operations. Map those operations to the ASIC gate set (H, X, Z, CNOT, Rx); reject or decompose unsupported gates. Entry point: e.g. `asic/qasm_loader.py` or `protocols/qasm_ingest.py` returning `list[Op]` compatible with [asic/circuit.py](../asic/circuit.py).
- **QIR:** If targeting LLVM QIR, add an adapter that reads QIR (e.g. from a QIR-to-QASM bridge or a small QIR parser) and maps to the same ASIC op list.
- **Pulse path:** Once the circuit is in ASIC op form, the existing [pulse/compiler.py](../pulse/compiler.py) can produce schedules; no change required there except documenting that the source can be QASM/QIR.

**Relevant files:** [asic/circuit.py](../asic/circuit.py), [asic/gate_set.py](../asic/gate_set.py), [pulse/compiler.py](../pulse/compiler.py).

---

### 4.2 GDS-to-MEEP Pipeline Hardening

**Goal:** Ensure a **frictionless bidirectional pipeline**: GDS (or geometry) → **slice/prepare** → **MEEP 3D FDTD** → **S-parameters** → use S-parameters to **auto-update** the Hamiltonian or topology model in [asic/topology.py](../asic/topology.py) (or a dedicated EM-aware model).

**Implementation directions:**

- **GDS → MEEP:** [engineering/heac/meep_unit_cell_sweep.py](../engineering/heac/meep_unit_cell_sweep.py) already runs unit-cell sweeps; [engineering/heac/manifest_to_gds.py](../engineering/heac/manifest_to_gds.py) produces GDS. Add a step that: (1) takes a GDS or a slice of it (e.g. one unit cell or a small cluster); (2) exports geometry to MEEP (e.g. via gdsfactory/gmeep or a custom script that reads GDS and builds MEEP geometry); (3) runs MEEP and extracts S-parameters (e.g. [engineering/meep_s_param_dataset.py](../engineering/meep_s_param_dataset.py) pattern).
- **S-parameters → Hamiltonian / topology:** Use the resulting S-parameter dataset to:
  - Train or update a **forward model** (e.g. [engineering/forward_prediction_net.py](../engineering/forward_prediction_net.py)) that maps design parameters to S-params; and/or
  - Derive **coupling or resonance parameters** (e.g. J, ω) for an effective Hamiltonian and feed them into [asic/topology.py](../asic/topology.py) or a separate “EM-informed” topology (e.g. edge weights or qubit frequencies from S-params).
- **Automation:** Optional pipeline flag (e.g. `--meep-verify`) that, after HEaC GDS generation, runs one or a few MEEP jobs and records S-param summary; CI can compare to baseline or fail if S-params drift beyond threshold.

**Relevant files:** [engineering/heac/meep_unit_cell_sweep.py](../engineering/heac/meep_unit_cell_sweep.py), [engineering/heac/manifest_to_gds.py](../engineering/heac/manifest_to_gds.py), [engineering/meep_s_param_dataset.py](../engineering/meep_s_param_dataset.py), [engineering/forward_prediction_net.py](../engineering/forward_prediction_net.py), [asic/topology.py](../asic/topology.py).

---

## Summary Table

| Domain | Item | Key existing files |
|--------|------|--------------------|
| Tapeout & LVS | Superconducting extraction (kinetic L, JJ) | heac/, parasitic_extraction.py, decoherence_rates.py |
| Tapeout & LVS | DFT & padframes | heac/manifest_to_gds.py, pdk_config.yaml, run_pipeline.py |
| Tapeout & LVS | Process variation (Monte Carlo) | parasitic_extraction.py, phases_to_geometry.py |
| Control & HIL | QICK / Zurich backends | pulse/compiler.py, openpulse_backend.py, pseudo_schedule.py |
| Control & HIL | HIL CI (pulse + calibration) | hardware-ci.yml, pulse/, calibration/run_calibration_cycle.py |
| Cryogenic | Thermal → decoherence (T₁/T₂) | thermal_stages.py, decoherence_rates.py, open_system_qutip.py |
| Cryogenic | Cryo-CMOS heat model | thermal_stages.py, routing_rl.py |
| Interop | OpenQASM 3.0 / QIR | asic/circuit.py, pulse/compiler.py |
| Interop | GDS–MEEP–S-param–Hamiltonian | heac/meep_unit_cell_sweep.py, meep_s_param_dataset.py, forward_prediction_net.py, asic/topology.py |

This roadmap can be used to prioritize issues, design doc updates, or implementation phases (e.g. “Tapeout readiness” vs “Control & HIL” vs “Cryogenic loop” vs “Interop”).
