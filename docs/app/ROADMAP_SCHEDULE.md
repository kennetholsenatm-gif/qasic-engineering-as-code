# Roadmap Schedule (Phases 3 and 4)

This document adds a **schedule layer** (target dates, dependencies, owners) for Phases 3 and 4 of the maturity roadmap. Implementation status (Done / Scaffold / Future) remains in [ROADMAP_STATUS.md](ROADMAP_STATUS.md). Detailed technical directions are in [NEXT_STEPS_ROADMAP.md](NEXT_STEPS_ROADMAP.md).

**Dates and owners are TBD;** the schedule is maintained by the solo developer as the project evolves. Placeholders (e.g. TBD, Q3) are used until updated.

---

## Phase 3: Packaging & Metasurface

| Item | Status (from ROADMAP_STATUS) | Target | Dependencies | Owner |
|------|------------------------------|--------|--------------|-------|
| 5.1 2D→3D CAD | Done | — | — | — |
| 5.2 Thermal/structural FEA | Done (stub) | — | — | — |
| 5.3 Flex routing | Done (stub) | — | — | — |
| 5.4 Magnetic shielding | Done (stub) | — | — | — |
| 6.1 Full-wave macro-sim | Scaffold | TBD | 6.2 (GNN) | TBD |
| 6.2 Physics-informed GNN | Done | — | — | — |
| 6.3 Cryogenic materials (Mattis–Bardeen) | Future | TBD | 6.1 (full-wave) | TBD |
| 6.4 Active/spatiotemporal metasurfaces | Future | TBD | 6.1, 6.3 | TBD |

---

## Phase 4: Control Methods & Fault Tolerance

| Item | Status (from ROADMAP_STATUS) | Target | Dependencies | Owner |
|------|------------------------------|--------|--------------|-------|
| 7.1 GRAPE/CRAB | Future | TBD | Pulse compiler, parasitic | TBD |
| 7.2 MIMO cancellation | Future | TBD | digital_twin | TBD |
| 7.3 System ID | Future | TBD | Calibration | TBD |
| 7.4 Dynamic metasurface control | Future | TBD | 7.1, pulse/compiler | TBD |
| 8.1 QEC-aware routing | Future | TBD | topology_builder, routing_rl | TBD |
| 8.2 Correlated error/TLS | Future | TBD | open_system_qutip | TBD |
| 8.3 Purcell filter generation | Future | TBD | HEaC / engineering | TBD |
| 8.4 Stim/PyMatching LER | Scaffold | TBD | qec_decoder_integration | TBD |

---

## When updating this schedule

1. Replace TBD with quarter or month (e.g. Q3, or specific month) as the project evolves.
2. Assign owner as solo dev or leave TBD.
3. Update dependencies if new blockers are identified.
4. Link from the main README for visibility.

Phases 1 and 2 are largely Done per [ROADMAP_STATUS.md](ROADMAP_STATUS.md); no schedule table is needed for them here.
