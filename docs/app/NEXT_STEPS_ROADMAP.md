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

## 5. Cryogenic Packaging & Mechanical Engineering (As Code)

Most quantum hardware teams treat the cryogenic package—sample holder, magnetic shields, wirebonds, and flex cables—as an artisanal, manual afterthought. By including [engineering/thermal_stages.py](../engineering/thermal_stages.py), [engineering/thermodynamic_validator.py](../engineering/thermodynamic_validator.py), and [engineering/superscreen_demo.py](../engineering/superscreen_demo.py) right alongside the chip layout and quantum state simulators, this framework treats the **entire physical environment as code**. That is how we solve the quantum I/O bottleneck. The following steps evolve cryogenic packaging and mechanical engineering within the same “as code” paradigm.

### 5.1 2D-to-3D Extrusion and Automated CAD Generation (CadQuery / build123d)

**Goal:** [engineering/heac/manifest_to_gds.py](../engineering/heac/manifest_to_gds.py) produces 2D planar lithography files. For cryogenic packaging we need the **3D physical manifestation**: sample holder, RF puck, and shielding cavities as machine-shop-ready geometry.

**Implementation directions:**

- Introduce a **programmatic 3D CAD** stack (e.g. **CadQuery** or **build123d**). Add a module that reads the ASIC geometry manifest (and optionally routing/die size) and generates **3D STEP files** for:
  - Copper or aluminum **sample holder** (cavity, mounting features).
  - **RF puck** (or equivalent carrier) with die cavity and wirebond clearance.
  - **Shielding cavities** (envelope for μ-metal or superconducting shield).
- **As-code win:** If a quantum engineer increases qubit count and expands die size by 2 mm in the manifest, the CI/CD pipeline should **automatically regenerate** a sample holder with a 2 mm larger cavity, adjust screw-hole placements, and output the new STEP file. Die size or qubit count in the manifest (or a packaging config derived from it) drives the 3D generator; no manual CAD handoff.
- **Integration:** New package or subfolder (e.g. `engineering/packaging/` or `engineering/cad_3d/`) with a script that consumes manifest + packaging parameters and writes STEP; optional `--packaging` or `--step` flag in [engineering/run_pipeline.py](../engineering/run_pipeline.py) to run after HEaC.

**Relevant files:** [engineering/heac/manifest_to_gds.py](../engineering/heac/manifest_to_gds.py), [engineering/heac/phases_to_geometry.py](../engineering/heac/phases_to_geometry.py), [engineering/run_pipeline.py](../engineering/run_pipeline.py).

---

### 5.2 CI/CD for Thermal & Structural FEA (Validation-as-Code)

**Goal:** [engineering/thermodynamic_validator.py](../engineering/thermodynamic_validator.py) provides lumped-element thermal budgeting (e.g. 10 mK stage cooling power vs coax heat leak). The next step is **automated Finite Element Analysis (FEA)** for thermal and structural validation.

**Implementation directions:**

- Integrate an **open-source FEA solver** (e.g. **FEniCS** or **Elmer**) to run:
  - **Differential thermal contraction** (300 K → 10 mK): ensure the package and die do not fracture due to CTE mismatch.
  - **Thermal gradient** simulation: ensure qubits remain properly thermalized (e.g. acceptable gradient across the chip).
- **As-code win:** When a PR changes the package design or substrate thickness, the CI pipeline should **automatically run** these FEA jobs and pass/fail (e.g. max stress below yield, max ΔT below spec). Validation becomes a first-class CI step alongside thermodynamic_validator.
- **Entry point:** New script (e.g. `engineering/structural_fea.py` or `engineering/packaging/thermal_fea.py`) that reads packaging geometry (from the 3D CAD step or a simplified mesh description), runs the solver, and outputs a report (stress, temperature field, pass/fail). Hardware CI job runs it when packaging or thermal config files change.

**Relevant files:** [engineering/thermodynamic_validator.py](../engineering/thermodynamic_validator.py), [engineering/thermal_stages.py](../engineering/thermal_stages.py), [.github/workflows/hardware-ci.yml](../.github/workflows/hardware-ci.yml).

---

### 5.3 Automated 3D RF Routing and Flex-Cable Generation

**Goal:** On-chip routing is addressed by [engineering/routing_rl.py](../engineering/routing_rl.py). The next challenge is **3D spatial routing** of high-density RF flex cables or coaxial bundles down the dilution refrigerator without exceeding the thermal budget or causing crosstalk.

**Implementation directions:**

- **Extend routing** to handle **3D flex-cable routing** (e.g. superconducting NbTi on polyimide) between stages (e.g. 4 K → 10 mK mixing chamber). Inputs: number of control lines, physical constraints (diameter of fridge plates, bend radii, layer stack).
- **Output:** Geometric layout of flex cables (centerlines, widths, layer assignment) and **thermal load** per stage (resistive loss, dielectric loss proxy) so that [engineering/thermal_stages.py](../engineering/thermal_stages.py) can consume it.
- **As-code win:** A script takes the required number of control lines, computes the flex layout that fits within the fridge plate diameter and bend rules, and **automatically** computes the resulting thermal load and feeds it back into the thermal budget. Change qubit count → change control-line count → re-route flex → re-run thermal validation.
- **Module:** New `engineering/flex_routing.py` (or under `engineering/packaging/`) that implements 3D routing (discrete path search or constraint-based layout) and outputs both geometry (for CAD or documentation) and a thermal summary (power per stage).

**Relevant files:** [engineering/routing_rl.py](../engineering/routing_rl.py), [engineering/thermal_stages.py](../engineering/thermal_stages.py), [engineering/thermodynamic_validator.py](../engineering/thermodynamic_validator.py).

---

### 5.4 Parametric Magnetic Shielding Generation

**Goal:** [engineering/superscreen_demo.py](../engineering/superscreen_demo.py) models the Meissner effect in superconducting films. Link this **directly to mechanical enclosure generation**: parametrically design μ-metal and superconducting (e.g. aluminum or niobium) shields from the required internal volume.

**Implementation directions:**

- **Parametric shield design:** From packaging config (internal volume, number of feedthroughs, wiring holes), generate the geometry of the **outer shields** (μ-metal and/or superconducting can). Hole sizes and positions are parameters (e.g. for ventilation and wiring).
- **Superscreen verification:** Run [engineering/superscreen_demo.py](../engineering/superscreen_demo.py) (or an extended wrapper) to simulate **ambient magnetic flux attenuation** for the proposed shield geometry. Compare to an acceptable threshold for the qubits.
- **As-code win:** An **automated optimization loop** adjusts the shield geometry (e.g. hole sizes, thickness, overlap) until the superscreen simulation verifies that flux is attenuated below the acceptable threshold. Shield design is driven by physics (superscreen) rather than by hand.
- **Integration:** New module (e.g. `engineering/packaging/magnetic_shield.py`) that: (1) generates shield CAD (or mesh) from params; (2) calls superscreen (or a reduced-order model) for attenuation; (3) optionally runs an optimizer (e.g. scipy) to meet the flux spec. Can feed into the same 3D CAD pipeline as §5.1 for a single STEP or assembly.

**Relevant files:** [engineering/superscreen_demo.py](../engineering/superscreen_demo.py), [engineering/heac/manifest_to_gds.py](../engineering/heac/manifest_to_gds.py), packaging/CAD pipeline from §5.1.

---

## 6. Metasurface Physics & Inverse Design Evolution

Based on the **Cryogenic Metamaterial Architectures**, **Holographic Metasurfaces for Quantum SATCOM**, and **GNN Inverse Design** whitepapers, the following steps evolve the metasurface pipeline from local phase approximation and room-temperature EM toward full-wave macro-simulation, physics-informed inverse design, cryogenic material models, and active (spatiotemporal) holographic control.

### 6.1 Shift from Local Phase Approximation to Full-Wave Macro-Simulations

**Goal:** The current pipeline relies on the **Local Phase Approximation (LPA)**—[engineering/heac/meep_unit_cell_sweep.py](../engineering/heac/meep_unit_cell_sweep.py) sweeps individual unit cells with periodic boundary conditions to build the meta-atom library, and [engineering/heac/phases_to_geometry.py](../engineering/heac/phases_to_geometry.py) stitches them together. The LPA breaks down when neighboring meta-atoms have drastically different geometries (strong mutual coupling and parasitic phase shifts).

**Implementation directions:**

- **Full-array FDTD:** Automate generation of FDTD scripts for the **entire, finite metasurface** macro-structure. A generator takes the synthesized GDS layout of the full array and pipes it into MEEP (or another finite-element solver).
- **Verification loop:** Synthesize the array from the unit-cell library → simulate the full array → compute the **actual far-field radiation pattern** to check for side-lobe degradation due to near-field coupling. Fail or warn in CI if pattern deviates from target beyond threshold.
- **As-code win:** Design and verification stay in code; no hand-off to a separate “full-wave check” step. Pipeline flag (e.g. `--full-wave-verify`) or a dedicated job that runs after HEaC GDS and outputs a radiation-pattern report.

**Relevant files:** [engineering/heac/meep_unit_cell_sweep.py](../engineering/heac/meep_unit_cell_sweep.py), [engineering/heac/phases_to_geometry.py](../engineering/heac/phases_to_geometry.py), [engineering/heac/manifest_to_gds.py](../engineering/heac/manifest_to_gds.py), [engineering/meep_s_param_dataset.py](../engineering/meep_s_param_dataset.py).

---

### 6.2 Physics-Informed Enhancements to the GNN Inverse Design

**Goal:** [engineering/metasurface_inverse_gnn.py](../engineering/metasurface_inverse_gnn.py) uses Graph Neural Networks to predict meta-atom geometry from S-parameters. Standard GNNs can output **un-fabable** geometries (e.g. minimum feature size or acute-angle violations already checked by [engineering/heac/run_drc_klayout.py](../engineering/heac/run_drc_klayout.py)).

**Implementation directions:**

- **Fabrication-aware loss:** Embed **fabrication constraints** and **physics-informed loss functions** directly into the GNN training loop. Beyond minimizing S-parameter MSE, heavily penalize geometries that violate DRC rules (min feature size, acute angles, spacing). Optionally use a differentiable DRC proxy or call DRC in the loop and backpropagate through a smooth surrogate.
- **As-code win:** A truly **end-to-end differentiable** pipeline where the inverse-design engine is natively aware of the foundry’s lithographic limits, yielding **zero DRC errors on first pass** (or near-zero with minimal post-correction).
- **Integration:** Extend the GNN loss in [engineering/metasurface_inverse_gnn.py](../engineering/metasurface_inverse_gnn.py) (or a wrapper) to include DRC penalty terms; optionally consume [engineering/heac/pdk_config.yaml](../engineering/heac/pdk_config.yaml) or a small “DRC rules for training” spec so the same rules used in run_drc_klayout.py are reflected in training.

**Relevant files:** [engineering/metasurface_inverse_gnn.py](../engineering/metasurface_inverse_gnn.py), [engineering/heac/run_drc_klayout.py](../engineering/heac/run_drc_klayout.py), [engineering/heac/pdk_config.yaml](../engineering/heac/pdk_config.yaml), [engineering/metasurface_inverse_net.py](../engineering/metasurface_inverse_net.py).

---

### 6.3 Native Cryogenic Material Models (Kinetic Inductance)

**Goal:** Operating metasurfaces at **deep cryogenic temperatures** (Quantum SATCOM, qubit interfacing) means standard classical EM models are insufficient. Superconducting meta-atoms exhibit **kinetic inductance**, which radically changes resonance frequency and phase response compared to room-temperature copper.

**Implementation directions:**

- **Mattis–Bardeen in MEEP:** Update MEEP material models to support **complex conductivity** (σ₁ − iσ₂) from **Mattis–Bardeen theory**. Parameterize [engineering/meep_s_param_dataset.py](../engineering/meep_s_param_dataset.py) by **temperature** and **London penetration depth** (or equivalent superconducting parameters).
- **Thermal feedback loop:** When [engineering/thermodynamic_validator.py](../engineering/thermodynamic_validator.py) or [engineering/thermal_stages.py](../engineering/thermal_stages.py) predicts a **temperature fluctuation** on the RF routing stage, the pipeline should: (1) re-compute the kinetic inductance shift; (2) update the S-parameters (or meta-atom library slice); (3) re-optimize or correct the meta-atom geometry to compensate for the thermal shift.
- **As-code win:** Thermal and EM models are coupled: temperature in → kinetic inductance → S-params → geometry correction. No manual “re-sweep at new T” hand-off.

**Relevant files:** [engineering/meep_s_param_dataset.py](../engineering/meep_s_param_dataset.py), [engineering/heac/meep_unit_cell_sweep.py](../engineering/heac/meep_unit_cell_sweep.py), [engineering/thermodynamic_validator.py](../engineering/thermodynamic_validator.py), [engineering/thermal_stages.py](../engineering/thermal_stages.py).

---

### 6.4 Spatiotemporal & Active Holographic Metasurfaces

**Goal:** For **SATCOM tracking**, static beamforming is insufficient; the metasurface must be **dynamically reconfigurable**. If tunable superconducting meta-atoms (e.g. DC-biased SQUIDs) alter the resonant phase, the codebase must track both the static GDS and the **control matrix** (DC flux bias lines) required to steer the beam.

**Implementation directions:**

- **From phases to states:** Extend [engineering/heac/phases_to_geometry.py](../engineering/heac/phases_to_geometry.py) conceptually to **states_to_geometry** (or a parallel path). The framework should output not only static GDS lithography but the **control matrix** mapping: which DC flux bias lines drive which meta-atoms, and the bias values (or lookup table) for a given beam state (e.g. steering angle vs time).
- **Pulse-plane link:** Connect this to the [pulse/](../pulse/) control plane. The compiler can **jointly** output: (1) microwave pulses for the quantum chip; (2) **synchronized low-frequency control signals** (DC or slow modulation) needed to steer the holographic metasurface beam toward a moving satellite.
- **As-code win:** One pipeline produces both “quantum control” (pulse schedules) and “metasurface control” (bias schedules); beam steering and qubit operations are co-designed and time-aligned in code.

**Relevant files:** [engineering/heac/phases_to_geometry.py](../engineering/heac/phases_to_geometry.py), [pulse/compiler.py](../pulse/compiler.py), [engineering/run_pipeline.py](../engineering/run_pipeline.py), [engineering/metasurface_inverse_net.py](../engineering/metasurface_inverse_net.py).

---

## 7. Control Methodologies (Rigorous Control-as-Code)

To enforce **rigorous control methodologies at every layer of the stack**, the following steps integrate optimal control, MIMO cancellation, closed-loop system identification, and dynamic metasurface control into the pipeline.

### 7.1 Optimal Control-as-Code (Integrating GRAPE/CRAB)

**Goal:** [pulse/compiler.py](../pulse/compiler.py) and [pulse/openpulse_backend.py](../pulse/openpulse_backend.py) map gate sets to standard analytical microwave envelopes (Gaussian, Cosine). Custom ASIC layouts introduce **spurious couplings** and **parasitic frequency shifts** that generic envelopes cannot suppress.

**Implementation directions:**

- **Integrate optimal control:** Plug **open-source optimal control** (e.g. `qutip.control` or Q-CTRL equivalents) directly into the compiler. When [engineering/heac/manifest_to_gds.py](../engineering/heac/manifest_to_gds.py) produces a layout, the pipeline should: (1) extract Hamiltonian parameters via [engineering/parasitic_extraction.py](../engineering/parasitic_extraction.py); (2) feed them into a **GRAPE** (Gradient Ascent Pulse Engineering) or **CRAB** solver; (3) synthesize **custom pulse envelopes** that suppress the exact leakage and crosstalk for that GDS iteration.
- **As-code win:** Layout changes automatically drive re-extraction and re-optimization of pulses. No manual “re-tune for this chip” step; the compiler produces layout-specific optimal envelopes in CI or at tape-out.

**Relevant files:** [pulse/compiler.py](../pulse/compiler.py), [pulse/openpulse_backend.py](../pulse/openpulse_backend.py), [engineering/heac/manifest_to_gds.py](../engineering/heac/manifest_to_gds.py), [engineering/parasitic_extraction.py](../engineering/parasitic_extraction.py).

---

### 7.2 MIMO Crosstalk Cancellation in the Digital Twin

**Goal:** High-density quantum ASICs suffer from **massive microwave crosstalk**. Single-input–single-output (SISO) calibration does not scale.

**Implementation directions:**

- **Full transfer matrix:** Extend [engineering/calibration/digital_twin.py](../engineering/calibration/digital_twin.py) to model the **full multi-qubit transfer matrix**. Implement **active MIMO (Multiple-Input Multiple-Output) control** via feedforward matrices in schedule generation (e.g. cancellation tones on adjacent lines).
- **CI-driven cancellation:** If [engineering/routing_rl.py](../engineering/routing_rl.py) places two readout lines too close, the CI/CD pipeline should: (1) detect elevated **S₂₁ crosstalk**; (2) compute a **cancellation tone** (inverted, out-of-phase pulse on the adjacent line); (3) inject it into [pulse/pseudo_schedule.py](../pulse/pseudo_schedule.py).
- **As-code win:** Routing and control are co-optimized; crosstalk is compensated in software before hardware ships, and CI enforces that schedules include the correct MIMO feedforward.

**Relevant files:** [engineering/calibration/digital_twin.py](../engineering/calibration/digital_twin.py), [engineering/routing_rl.py](../engineering/routing_rl.py), [pulse/pseudo_schedule.py](../pulse/pseudo_schedule.py), [.github/workflows/hardware-ci.yml](../.github/workflows/hardware-ci.yml).

---

### 7.3 Closed-Loop System Identification (System ID)

**Goal:** [engineering/calibration/run_calibration_cycle.py](../engineering/calibration/run_calibration_cycle.py) and [engineering/calibration/bayesian_update.py](../engineering/calibration/bayesian_update.py) provide the scaffold for automated tuning. The next step is **Hamiltonian tomography**: infer the actual system parameters from telemetry and use them to recompute schedules.

**Implementation directions:**

- **Hamiltonian Tomography protocol:** Standardize a set of **probing pulses** run on the [engineering/open_system_qutip.py](../engineering/open_system_qutip.py) model (or on hardware). Collect “telemetry” per [engineering/calibration/telemetry_schema.py](../engineering/calibration/telemetry_schema.py) and use **Bayesian inference** to reconstruct the underlying Hamiltonian (e.g. qubit frequencies, coupling strengths, anharmonicities).
- **Self-healing digital twin:** Validate the loop by **injecting artificial fabrication defects** in simulation (e.g. 10% drift in Josephson energy). Assert that the Bayesian updater: (1) identifies the drift; (2) recalculates the pulse schedule; (3) restores **gate fidelity above 99.9%**.
- **As-code win:** A **self-healing** digital twin: calibration and system-ID run in lockstep, and the pipeline can prove robustness to parameter drift in CI.

**Relevant files:** [engineering/calibration/run_calibration_cycle.py](../engineering/calibration/run_calibration_cycle.py), [engineering/calibration/bayesian_update.py](../engineering/calibration/bayesian_update.py), [engineering/calibration/telemetry_schema.py](../engineering/calibration/telemetry_schema.py), [engineering/open_system_qutip.py](../engineering/open_system_qutip.py).

---

### 7.4 Dynamic Control of Metasurfaces

**Goal:** For **SATCOM** and holographic metasurface components ([engineering/metasurface_inverse_gnn.py](../engineering/metasurface_inverse_gnn.py)), **static** phase arrays are insufficient for tracking low-earth-orbit quantum satellites. The control plane must schedule **dynamic** spatiotemporal flux biases and respect hardware limits.

**Implementation directions:**

- **Dynamic control constraints:** Define the **dynamic control constraints** for the metasurface: if unit cells are tuned via **fast-flux lines**, model the **bandwidth and latency** of the control electronics (AWGs) driving those lines.
- **Joint scheduling:** Extend the control plane so [pulse/compiler.py](../pulse/compiler.py) does not only schedule qubit logic gates, but **jointly** schedules the **macroscopic spatiotemporal flux biases** required to continuously steer the metasurface beam. **Verify** that control signals do not exceed AWG bandwidth or slew-rate limits.
- **As-code win:** One compiler produces both qubit pulse schedules and metasurface steering schedules; beam tracking and gate execution are time-aligned, and CI checks that all control signals stay within hardware specs.

**Relevant files:** [engineering/metasurface_inverse_gnn.py](../engineering/metasurface_inverse_gnn.py), [pulse/compiler.py](../pulse/compiler.py), [engineering/heac/phases_to_geometry.py](../engineering/heac/phases_to_geometry.py) (or states_to_geometry), control-plane docs.

---

## 8. Fault Tolerance & Noise Resilience

To build a **truly fault-tolerant ASIC**, the physical layout must suppress noise inherently and accommodate the **routing overhead of syndrome measurements**. The following steps mature the FT and noise-resilience story of the framework.

### 8.1 QEC-Aware Topological Routing Constraints

**Goal:** [engineering/routing_rl.py](../engineering/routing_rl.py) and [asic/topology_builder.py](../asic/topology_builder.py) focus on connecting qubits for general algorithms or specific protocols. **Fault tolerance** requires **strict geometric lattice embeddings** (e.g. Surface Code → 2D grid; Heavy-Hex; Color Codes → trivalent tessellations).

**Implementation directions:**

- **Topological rule checks:** Introduce **“Topological Rule Checks”** into the router. If the manifest declares a target logical qubit using a distance-*d* surface code (e.g. *d* = 3), the RL agent must be **constrained** to output a planar embedding where **data and measure qubits strictly alternate**, and **crosstalk-prone diagonal crossings** are physically banned.
- **As-code win:** When an engineer requests a logical qubit, the pipeline automatically **synthesizes the correct physical sub-grid**, routes the high-bandwidth **syndrome extraction lines to the perimeter**, and **proves via KLayout DRC** that the QEC topology has not been violated.
- **Integration:** Extend the manifest (or a QEC config) to specify code family and distance; topology_builder and routing_rl consume these constraints; [engineering/heac/run_drc_klayout.py](../engineering/heac/run_drc_klayout.py) (or a dedicated QEC-topology checker) validates the layout against the declared code.

**Relevant files:** [engineering/routing_rl.py](../engineering/routing_rl.py), [asic/topology_builder.py](../asic/topology_builder.py), [engineering/heac/manifest_to_gds.py](../engineering/heac/manifest_to_gds.py), [engineering/heac/run_drc_klayout.py](../engineering/heac/run_drc_klayout.py).

---

### 8.2 Spatially Correlated Error & TLS Modeling

**Goal:** [engineering/open_system_qutip.py](../engineering/open_system_qutip.py) handles Lindbladian master equations with **Markovian, independent** errors. Fault tolerance is threatened by **correlated errors** (e.g. cosmic ray impact, phonon bursts through the substrate) and **1/*f* Two-Level System (TLS)** defects.

**Implementation directions:**

- **Correlated noise generator:** Link [engineering/parasitic_extraction.py](../engineering/parasitic_extraction.py) and [engineering/thermodynamic_validator.py](../engineering/thermodynamic_validator.py) to a **correlated noise generator**. If the GDS places two qubits on a **continuous shared dielectric pad** without phononic bandgap trenching, the model should automatically **inject correlated multi-qubit Pauli errors** into the state simulator.
- **As-code win:** Run **automated CI tests** to verify that the physical layout (trenching, ground planes) **breaks the spatial correlation** of errors, so the **physical error rate stays below the theoretical pseudo-threshold** of the chosen QEC code.
- **Output:** A “correlation report” (which qubit pairs share substrate, predicted correlation length) and a pass/fail vs. pseudo-threshold; optionally feed into a decoder pipeline (§8.4) for logical error rate.

**Relevant files:** [engineering/open_system_qutip.py](../engineering/open_system_qutip.py), [engineering/parasitic_extraction.py](../engineering/parasitic_extraction.py), [engineering/thermodynamic_validator.py](../engineering/thermodynamic_validator.py), [engineering/heac/manifest_to_gds.py](../engineering/heac/manifest_to_gds.py).

---

### 8.3 Passive Protection and Purcell Filter Generation

**Goal:** Outside active control, **passive environmental decoupling** is essential. **Spontaneous emission (*T*₁ relaxation)** via readout resonators is a major noise source.

**Implementation directions:**

- **Parametric Purcell filters:** Use existing EM hooks ([engineering/heac/meep_unit_cell_sweep.py](../engineering/heac/meep_unit_cell_sweep.py)) to **parametrically generate Purcell filters**. The code should automatically **append a bandpass filter geometry** between the readout resonator and the feedline in the GDS layout.
- **As-code win:** The pipeline takes a **target *T*₁ limit** and **readout bandwidth**, automatically **synthesizes the stepped-impedance geometry** of the Purcell filter, **simulates it in MEEP**, and **adjusts the layout** until the physical filter guarantees the required environmental decoupling.
- **Module:** New component (e.g. in `engineering/heac/` or `engineering/`) that: (1) accepts *T*₁ and BW specs; (2) designs filter dimensions; (3) runs MEEP (or equivalent) for *Q* and coupling; (4) outputs GDS snippets or directives for manifest_to_gds to place the filter in the layout.

**Relevant files:** [engineering/heac/meep_unit_cell_sweep.py](../engineering/heac/meep_unit_cell_sweep.py), [engineering/heac/manifest_to_gds.py](../engineering/heac/manifest_to_gds.py), [engineering/decoherence_rates.py](../engineering/decoherence_rates.py).

---

### 8.4 Direct Integration with a QEC Decoder (e.g. PyMatching)

**Goal:** To assess whether the ASIC is **actually useful**, the pipeline must compute the **logical error rate**, not only physical fidelity.

**Implementation directions:**

- **MWPM decoder:** Integrate a fast **Minimum Weight Perfect Matching (MWPM)** decoder such as **PyMatching** or **Stim**. Map the physical layout and noise model to a **Stim circuit** (or equivalent), run a simulated **syndrome extraction loop**, and output the **predicted Logical Error Rate (LER)** under realistic physical noise.
- **End-to-end logical yield:** (1) Generate the physical GDS. (2) Extract parasitic noise and crosstalk. (3) **Map those hardware noise values** to a Stim circuit. (4) Run a simulated syndrome extraction loop. (5) **Output the predicted LER** of the ASIC. Optionally gate tape-out or design iteration on LER below a target.
- **As-code win:** **Logical yield prediction** in CI or pre-tape-out: change layout or routing → re-extract noise → re-run decoder → get new LER. Design decisions are driven by logical performance, not only by physical metrics.

**Relevant files:** [engineering/parasitic_extraction.py](../engineering/parasitic_extraction.py), [engineering/heac/manifest_to_gds.py](../engineering/heac/manifest_to_gds.py), [asic/topology_builder.py](../asic/topology_builder.py), [engineering/open_system_qutip.py](../engineering/open_system_qutip.py); external: Stim, PyMatching.

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
| Cryo packaging | 2D→3D CAD (CadQuery/build123d), STEP sample holder | heac/manifest_to_gds.py, phases_to_geometry.py, run_pipeline.py |
| Cryo packaging | CI/CD thermal & structural FEA (FEniCS/Elmer) | thermodynamic_validator.py, thermal_stages.py, hardware-ci.yml |
| Cryo packaging | 3D RF flex routing, thermal feedback | routing_rl.py, thermal_stages.py, thermodynamic_validator.py |
| Cryo packaging | Parametric magnetic shielding (superscreen-driven) | superscreen_demo.py, heac/manifest_to_gds.py |
| Metasurface physics | Full-wave macro-sim (LPA → full-array FDTD, far-field verify) | heac/meep_unit_cell_sweep.py, phases_to_geometry.py, manifest_to_gds.py, meep_s_param_dataset.py |
| Metasurface physics | Physics-informed GNN (DRC/fab constraints in loss) | metasurface_inverse_gnn.py, heac/run_drc_klayout.py, pdk_config.yaml |
| Metasurface physics | Cryogenic materials (Mattis–Bardeen, T & λ in meep_s_param) | meep_s_param_dataset.py, meep_unit_cell_sweep.py, thermodynamic_validator.py, thermal_stages.py |
| Metasurface physics | Active/spatiotemporal (states_to_geometry, control matrix, pulse link) | phases_to_geometry.py, pulse/compiler.py, run_pipeline.py, metasurface_inverse_net.py |
| Control methodologies | Optimal control (GRAPE/CRAB, layout→parasitic→Hamiltonian→pulses) | pulse/compiler.py, openpulse_backend.py, heac/manifest_to_gds.py, parasitic_extraction.py |
| Control methodologies | MIMO crosstalk cancellation (transfer matrix, feedforward, CI S₂₁→cancel tone) | calibration/digital_twin.py, routing_rl.py, pseudo_schedule.py, hardware-ci.yml |
| Control methodologies | Closed-loop System ID (Hamiltonian tomography, Bayesian, self-healing twin) | run_calibration_cycle.py, bayesian_update.py, telemetry_schema.py, open_system_qutip.py |
| Control methodologies | Dynamic metasurface control (flux bias BW/latency, joint qubit+beam schedule, AWG limits) | metasurface_inverse_gnn.py, pulse/compiler.py, phases_to_geometry.py |
| Fault tolerance & noise | QEC-aware topological routing (lattice constraints, syndrome lines, DRC topology check) | routing_rl.py, topology_builder.py, manifest_to_gds.py, run_drc_klayout.py |
| Fault tolerance & noise | Spatially correlated error & TLS (correlated noise generator, CI vs pseudo-threshold) | open_system_qutip.py, parasitic_extraction.py, thermodynamic_validator.py, manifest_to_gds.py |
| Fault tolerance & noise | Purcell filter generation (T₁/BW → stepped-impedance GDS, MEEP verify) | heac/meep_unit_cell_sweep.py, manifest_to_gds.py, decoherence_rates.py |
| Fault tolerance & noise | QEC decoder integration (Stim/PyMatching, hardware noise→LER, logical yield prediction) | parasitic_extraction.py, manifest_to_gds.py, topology_builder.py, open_system_qutip.py |

This roadmap can be used to prioritize issues, design doc updates, or implementation phases (e.g. “Tapeout readiness” vs “Control & HIL” vs “Cryogenic loop” vs “Interop” vs “Cryo packaging” vs “Metasurface physics” vs “Control methodologies” vs “Fault tolerance & noise”).
