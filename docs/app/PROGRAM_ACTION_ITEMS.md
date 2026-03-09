# Program Action Items (TPM Feedback Index)

This document maps the **Monarch Quantum Sr. Director / TPM feedback** to the deliverables and immediate next steps. It keeps the feedback and the new docs in one place for the TPM and the team.

---

## 1. Programmatic (scope, roadmap, customer)

| Feedback theme | Deliverable | Doc |
|----------------|-------------|-----|
| **Scope management / "everything" problem** | Define Alpha scope; single golden path; list what is parked. | [ALPHA_SCOPE.md](ALPHA_SCOPE.md) |
| **Roadmap as checklist, not schedule** | Add timeline, dependencies, and owners for Phases 3–4. | [ROADMAP_SCHEDULE.md](ROADMAP_SCHEDULE.md) |
| **Customer and business alignment** | Define primary Alpha customer (internal vs external vs hybrid); implications for prioritization. | [ALPHA_CUSTOMER.md](ALPHA_CUSTOMER.md). **Done:** Internal hardware engineering team chosen. |

---

## 2. Technical risk (sim validation, compute cost, dependency bloat)

| Feedback theme | Deliverable | Doc |
|----------------|-------------|-----|
| **Simulation vs physical reality gap** | Plan to validate FDTD and thermal-to-decoherence against real data; first silicon / test structures. | [SIMULATION_VALIDATION_STRATEGY.md](SIMULATION_VALIDATION_STRATEGY.md) |
| **Compute cost and cloud architecture** | Cost and margin assessment for DAGs (local, IBM, EKS); budget guardrail. | [COMPUTE_COST_ASSESSMENT.md](COMPUTE_COST_ASSESSMENT.md) |
| **Dependency bloat / control vs data plane** | Proposal: slim control plane (API) vs heavy data plane (workers). | [ARCHITECTURE_CONTROL_VS_DATA_PLANE.md](ARCHITECTURE_CONTROL_VS_DATA_PLANE.md). **Done:** Slim API image (Dockerfile.api) and dedicated worker image (Dockerfile.worker) implemented; sync pipeline and protocol run via Celery when API is slim. |

---

## 3. Immediate next steps (2 sprints)

| Next step (from TPM) | Action | Doc / cadence |
|----------------------|--------|----------------|
| **Define the Alpha milestone** | Lock scope (golden path only), acceptance criteria, and optional Alpha mode. | [ALPHA_SCOPE.md](ALPHA_SCOPE.md); **45-min kickoff** to confirm. |
| **Roadmap workshop** | Cross-functional (Software, Hardware, Quantum) review of ROADMAP_STATUS; map Phases 3–4 to calendar, dependencies, owners. | [ROADMAP_SCHEDULE.md](ROADMAP_SCHEDULE.md); **45-min kickoff** and follow-up workshop. |
| **Architecture review for modularization** | Proposal for splitting into qasic-ui, qasic-orchestrator, qasic-compute-workers; deploy boundaries and migration path. | [ARCHITECTURE_MODULARIZATION_PROPOSAL.md](ARCHITECTURE_MODULARIZATION_PROPOSAL.md); **45-min kickoff** to assign owner. |
| **Establish the feedback loop** | Bi-weekly cadence: review pipeline metrics (GDS success rate, latency, failure reasons); track vs requirements. | [PIPELINE_METRICS.md](PIPELINE_METRICS.md); bi-weekly meeting + summary. |

---

## 4. 45-min kickoff

Schedule 45 minutes with the TPM to:

1. **Alpha definition:** Confirm [ALPHA_SCOPE.md](ALPHA_SCOPE.md) and [ALPHA_CUSTOMER.md](ALPHA_CUSTOMER.md) (primary customer, acceptance criteria).
2. **Roadmap:** Confirm workshop date and attendees for Phases 3–4 schedule and owners.
3. **Modularization:** Assign owner for [ARCHITECTURE_MODULARIZATION_PROPOSAL.md](ARCHITECTURE_MODULARIZATION_PROPOSAL.md) and next steps (slim API image, etc.).
4. **Feedback loop:** Confirm bi-weekly cadence and who runs the pipeline metrics review.

After the kickoff, update the relevant docs with decisions and dates.
