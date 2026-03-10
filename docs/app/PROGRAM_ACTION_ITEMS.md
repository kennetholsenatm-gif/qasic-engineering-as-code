# Program Action Items

This document tracks **prioritization and deliverables** for the solo developer. It keeps scope, roadmap, and next steps in one place.

---

## 1. Programmatic (scope, roadmap, focus)

| Theme | Deliverable | Doc |
|-------|-------------|-----|
| **Scope management / "everything" problem** | Define Alpha scope; pipeline scope: any OpenQASM 2/3, any qubit count → digital-twin ASIC; list what is parked. | [ALPHA_SCOPE.md](ALPHA_SCOPE.md) |
| **Roadmap as checklist, not schedule** | Add timeline, dependencies, and owners for Phases 3–4. | [ROADMAP_SCHEDULE.md](ROADMAP_SCHEDULE.md) |
| **Alpha focus** | Define primary use case for Alpha (digital-twin pipeline, solo dev). | [ALPHA_CUSTOMER.md](ALPHA_CUSTOMER.md). **Done:** Digital-twin pipeline for solo dev (see ALPHA_CUSTOMER). |

---

## 2. Technical risk (sim validation, compute cost, dependency bloat)

| Theme | Deliverable | Doc |
|-------|-------------|-----|
| **Simulation vs physical reality gap** | Plan to validate FDTD and thermal-to-decoherence against real data when/if available; first silicon / test structures are hypothetical for the digital twin. | [SIMULATION_VALIDATION_STRATEGY.md](SIMULATION_VALIDATION_STRATEGY.md) |
| **Compute cost and cloud architecture** | Cost and margin assessment for DAGs (local, IBM, EKS); budget guardrail. | [COMPUTE_COST_ASSESSMENT.md](COMPUTE_COST_ASSESSMENT.md) |
| **Dependency bloat / control vs data plane** | Proposal: slim control plane (API) vs heavy data plane (workers). | [ARCHITECTURE_CONTROL_VS_DATA_PLANE.md](ARCHITECTURE_CONTROL_VS_DATA_PLANE.md). **Done:** Slim API image (Dockerfile.api) and dedicated worker image (Dockerfile.worker) implemented; sync pipeline and protocol run via Celery when API is slim. |

---

## 3. Immediate next steps

| Next step | Action | Doc |
|-----------|--------|-----|
| **Define the Alpha milestone** | Lock scope (golden path only), acceptance criteria, and optional Alpha mode. | [ALPHA_SCOPE.md](ALPHA_SCOPE.md) |
| **Roadmap** | Map Phases 3–4 to calendar, dependencies, owners (solo dev backlog). | [ROADMAP_SCHEDULE.md](ROADMAP_SCHEDULE.md) |
| **Architecture review for modularization** | Proposal for splitting into qasic-ui, qasic-orchestrator, qasic-compute-workers; deploy boundaries and migration path. | [ARCHITECTURE_MODULARIZATION_PROPOSAL.md](ARCHITECTURE_MODULARIZATION_PROPOSAL.md) |
| **Pipeline health** | Track pipeline metrics (GDS success rate, latency, failure reasons) per [PIPELINE_METRICS.md](PIPELINE_METRICS.md); optional periodic self-review. | [PIPELINE_METRICS.md](PIPELINE_METRICS.md) |

---

## 4. When refining scope or roadmap

When refining scope or roadmap, update [ALPHA_SCOPE.md](ALPHA_SCOPE.md), [ALPHA_CUSTOMER.md](ALPHA_CUSTOMER.md), and [ROADMAP_SCHEDULE.md](ROADMAP_SCHEDULE.md) as needed. No formal meetings or external stakeholders; the schedule is maintained by the solo developer as the project evolves.
