# Maturity Roadmap Implementation Status

This file tracks implementation status for [NEXT_STEPS_ROADMAP.md](NEXT_STEPS_ROADMAP.md). See the plan in `.cursor/plans/` and the roadmap summary table in NEXT_STEPS_ROADMAP.md.

## Phase 1: Tapeout & Control/HIL

| Item | Status | Notes |
|------|--------|--------|
| 1.1 Superconducting extraction | Done | `engineering/superconducting_extraction.py` |
| 1.2 DFT & padframes | Done | `engineering/heac/dft_structures.py`, `--dft` in run_pipeline |
| 1.3 Process variation (Monte Carlo) | Done | `engineering/process_variation_sweep.py` |
| 2.1 QICK / Zurich backends | Done | `pulse/qick_export.py`, `pulse/zurich_export.py`, `--backend qick|zurich` |
| 2.2 HIL CI | Done | `.github/workflows/hardware-ci.yml` + `tests/test_hil_ci.py` |

## Phase 2: Cryogenic & Interop

| Item | Status | Notes |
|------|--------|--------|
| 3.1 Thermal → decoherence | Done | `engineering/thermal_to_decoherence.py` |
| 3.2 Cryo-CMOS heat model | Done | `--classical-power-nw` in thermal_stages, docs |
| 4.1 OpenQASM 3.0 / QIR | Done | `asic/qasm_loader.py` |
| 4.2 GDS–MEEP hardening | Done | `engineering/meep_verify.py`, `--meep-verify` |

## Phase 3: Packaging & Metasurface

| Item | Status | Notes |
|------|--------|--------|
| 5.1 2D→3D CAD | Done | `engineering/packaging/cad_3d.py`, `--packaging` |
| 5.2 Thermal/structural FEA | Done | `engineering/packaging/thermal_fea.py` (stub) |
| 5.3 Flex routing | Done | `engineering/flex_routing.py` (stub) |
| 5.4 Magnetic shielding | Done | `engineering/packaging/magnetic_shield.py` (stub) |
| 6.1 Full-wave macro-sim | Scaffold | Pipeline flag `--meep-verify`; full-array FDTD in meep_* |
| 6.2 Physics-informed GNN | Done | `drc_penalty_tensor()` in metasurface_inverse_gnn.py |
| 6.3 Cryogenic materials (Mattis–Bardeen) | Future | meep_s_param_dataset.py extension |
| 6.4 Active/spatiotemporal metasurfaces | Future | states_to_geometry, control matrix |

## Phase 4: Control Methods & Fault Tolerance

| Item | Status | Notes |
|------|--------|--------|
| 7.1 GRAPE/CRAB | Future | pulse/compiler + parasitic → qutip.control |
| 7.2 MIMO cancellation | Future | digital_twin.py transfer matrix |
| 7.3 System ID | Future | calibration Hamiltonian tomography |
| 7.4 Dynamic metasurface control | Future | pulse/compiler joint schedule |
| 8.1 QEC-aware routing | Future | topology_builder + routing_rl constraints |
| 8.2 Correlated error/TLS | Future | open_system_qutip + noise generator |
| 8.3 Purcell filter generation | Future | engineering/heac/ or engineering/ |
| 8.4 Stim/PyMatching LER | Scaffold | `engineering/qec_decoder_integration.py` |

## How to run

- **Pipeline:** `python engineering/run_pipeline.py --heac --gds --drc --thermal --parasitic --dft --meep-verify --packaging` (optional flags as needed).
- **Tests:** `python -m pytest tests/test_hil_ci.py tests/test_heac_drc_lvs.py tests/test_asic.py -v`.
