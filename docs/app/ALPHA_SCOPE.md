# Alpha Scope

This document defines what is **in scope** and **out of scope** for the Alpha milestone of QASIC Engineering-as-Code. It supports predictable execution by limiting scope to a single golden path until the core pipeline is stable.

See also [ALPHA_CUSTOMER.md](ALPHA_CUSTOMER.md) (who Alpha is for) and [PROGRAM_ACTION_ITEMS.md](PROGRAM_ACTION_ITEMS.md) (TPM feedback index).

---

## In scope for Alpha

**Single golden path only:** 3-qubit linear chain → canvas/QASM → routing → inverse design → HEaC → GDS output.

| Step | Description | References |
|------|-------------|------------|
| 1. Circuit input | User provides a project and circuit (OpenQASM 2 or 3) from the canvas; 3-qubit linear topology. | [OPENQASM_TO_ASIC_PIPELINE.md](OPENQASM_TO_ASIC_PIPELINE.md), Run Pipeline UI |
| 2. QASM → ASIC | Parse, gate-set mapping, interaction graph, topology, geometry manifest, superconducting extraction. | `src/core_compute/asic/qasm_loader.py`, `qasm_to_asic_pipeline.py` |
| 3. Routing | Circuit-derived routing (QAOA or RL); output mapping and `*_routing.json`. | `routing_qubo_qaoa.py`, `routing_rl.py` |
| 4. Inverse design | Phase profile from inverse net (MLP/GNN); output `*_inverse.json`, `*_inverse_phases.npy`. | `run_pipeline.py --skip-routing`, `metasurface_inverse_net.py` |
| 5. HEaC + GDS | Phases → geometry manifest → GDS via manifest_to_gds (requires gdsfactory). | `run_pipeline.py --heac --gds`, [HEaC_opensource_Meep.md](HEaC_opensource_Meep.md) |

**Entry points:** Web UI (Run Pipeline: project + circuit, full pipeline with circuit, Enable HEaC) or CLI: `python src/core_compute/engineering/run_pipeline.py -o pipeline_result --heac --gds` (with routing inputs prepared).

---

## Out of scope (parked)

The following are explicitly **not** part of Alpha. They remain in the repo but are not required for Alpha sign-off.

| Item | Rationale |
|------|-----------|
| **BQTC (Bayesian-Quantum Traffic Controller)** | Park until core pipeline is stable. Application layer. |
| **qrnc (quantum-backed tokens / exchange)** | Park until core pipeline is stable. Application layer. |
| **IaC Orchestrator UI** | Separate concern (infra DAG); not on the circuit→GDS critical path. |
| **Extra protocols beyond minimal chain** | Alpha focuses on 3-qubit linear; other protocols (QKD, teleportation, etc.) are demos, not Alpha acceptance. |
| **Workflows DAG builder** | Custom user-defined DAGs; park until the fixed pipeline (routing → inverse → HEaC → GDS) is stable and measurable. |
| **Full Phase 3/4 roadmap features** | Purcell filters, GRAPE/CRAB, QEC-aware routing, etc. are post-Alpha per [ROADMAP_STATUS.md](ROADMAP_STATUS.md). |

---

## Acceptance criteria for "Alpha done"

1. **User can run one flow end-to-end:** Select a project, provide a circuit (3-qubit linear chain, OpenQASM 2 or 3), run the full pipeline with HEaC and GDS enabled.
2. **Outputs:** Downloadable GDS file and a run record (task result, artifacts) visible in the UI or via API.
3. **Documentation:** This scope doc, Alpha customer doc, and a short runbook for the golden path (or link to [OPENQASM_TO_ASIC_WUI_WALKTHROUGH.md](OPENQASM_TO_ASIC_WUI_WALKTHROUGH.md)).
4. **Stability:** Pipeline success rate and latency tracked per [PIPELINE_METRICS.md](PIPELINE_METRICS.md); no blocking bugs on the golden path.

Criteria will be confirmed and refined in the Alpha kickoff (45-min workshop).
