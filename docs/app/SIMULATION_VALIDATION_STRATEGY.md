# Simulation–Fabrication Validation Strategy

This document outlines how we plan to **validate** FDTD (MEEP) and thermal-to-decoherence models against **real physical data** when/if such data exists (e.g. first silicon, test structures). This is a digital-twin project with no lab or fab; "first silicon" and measured data are hypothetical/future—the validation strategy applies when refining the digital twin against any future measured data. Closing the sim–fabrication gap remains a technical consideration for the pipeline.

See [ROADMAP_STATUS.md](ROADMAP_STATUS.md) and [HEaC_opensource_Meep.md](HEaC_opensource_Meep.md) for the current pipeline and HEaC stack.

---

## 1. Current simulation assets

| Asset | Purpose | Location |
|-------|---------|----------|
| **MEEP / FDTD** | Unit-cell and full-array EM validation; S-parameters, resonance. | [meep_verify.py](../../src/core_compute/engineering/meep_verify.py), `--meep-verify` in run_pipeline; [HEaC_opensource_Meep.md](HEaC_opensource_Meep.md) |
| **Thermal → decoherence** | Map thermal budget (10 mK / 4 K / 50 K) and classical power to decoherence rates for routing/simulation. | [thermal_to_decoherence.py](../../src/core_compute/engineering/thermal_to_decoherence.py) |
| **Thermal stages** | Lumped thermal model (dilution fridge stages); classical power per cell (e.g. 18 nW). | [thermal_stages.py](../../src/core_compute/engineering/thermal_stages.py), `--thermal` in run_pipeline |
| **Parasitic extraction** | Layout-aware L/C and decoherence from geometry manifest. | [parasitic_extraction.py](../../src/core_compute/engineering/parasitic_extraction.py) |

These produce **simulation-only** outputs (manifest, phases, GDS, reports). They are not yet compared to measured data from fabricated devices.

---

## 2. Risk: gap between simulation and fabrication

- **FDTD vs measured S-parameters:** Unit-cell or array response in MEEP may not match measured S-parameters (e.g. from VNA) due to material models, boundary conditions, or process variation.
- **Thermal and decoherence:** Predicted T1/T2 or decoherence rates from thermal and parasitic models may not match measured qubit coherence on real chips.
- **Geometry and GDS:** Manifest-to-GDS and DRC/LVS ensure layout correctness but do not guarantee that simulated performance matches fabricated performance.

Without a validation plan, we cannot quantify or reduce this gap.

---

## 3. Mitigation: validation plan (TBD when refined)

**Objectives:**

1. **First silicon / test structures:** Define which test structures (e.g. standalone resonators, single JJs, small circuits) will be fabricated and measured. Align with [ROADMAP_STATUS.md](ROADMAP_STATUS.md) (e.g. DFT witness structures, 1.2).
2. **Data collection:** Specify what will be measured (S-params, T1/T2, linewidth, Ic/Rn) and in what format. Store in a known location (e.g. calibration DB or artifact store) for comparison.
3. **Comparison criteria:** Define how we compare sim to measured (e.g. S-parameter error norm, T1/T2 within X%, resonance frequency within Y MHz). Set targets for “sim validated” (e.g. within 20% on key metrics).
4. **Timeline:** Assign target dates (e.g. first silicon by quarter X, first comparison report by Y) when the validation plan is refined.

**Output:** A short **validation runbook** (or section in this doc) that lists: test structures, measurement protocol, comparison script or pipeline, and ownership. Update [ROADMAP_SCHEDULE.md](ROADMAP_SCHEDULE.md) with validation milestones once agreed.

---

## 4. References

- [ROADMAP_STATUS.md](ROADMAP_STATUS.md) — Phase 3/4 items (full-wave macro-sim, cryogenic materials).
- [HEaC_opensource_Meep.md](HEaC_opensource_Meep.md) — HEaC tool chain and MEEP usage.
- [THERMAL_AND_PARASITICS.md](THERMAL_AND_PARASITICS.md) — Thermal stages and parasitic extraction.
