# Compute Cost Assessment

This document addresses the **financial margin** and **compute cost** of running the hybrid compute dispatcher at scale. The dispatcher routes work to local, IBM Quantum, or EKS ([dispatcher.py](../../src/backend/dispatcher.py)). Running Monte Carlo, full-wave MEEP, and ML models (PyTorch) can consume significant cloud credits; we need a cost view and guardrails.

See [ARCHITECTURE_CONTROL_VS_DATA_PLANE.md](ARCHITECTURE_CONTROL_VS_DATA_PLANE.md) for the split between control and data plane.

---

## 1. DAG types that drive cost

| Workload type | Where it runs | Typical cost drivers |
|---------------|---------------|----------------------|
| **Routing (QAOA)** | Local or IBM QPU | IBM: per-job QPU time; local: CPU. QAOA scales poorly beyond ~6 qubits; RL path used for larger. |
| **Routing (RL)** | Local | CPU only; scalable. |
| **Inverse design (MLP/GNN)** | Local (or future EKS) | PyTorch; CPU or GPU. Training or inference time. |
| **MEEP / FDTD** | Local (or future EKS) | CPU-heavy; full-array FDTD can be long-running. |
| **Monte Carlo (process variation)** | Local | Many runs of parasitic/superconducting extraction; CPU. |
| **Protocol on IBM** | IBM QPU | Per-job QPU time and queue. |
| **Pipeline (full)** | Celery workers (local or EKS) | Sum of routing + inverse + HEaC + optional MEEP/thermal. |

---

## 2. Placeholder: cost per run (TBD)

| Workload type | Typical run time | Estimated cost per run | Notes |
|---------------|------------------|------------------------|------|
| Circuit-to-ASIC only | &lt; 1 min | TBD | Mostly parsing and graph. |
| Routing (QAOA, 3–6 qubits) | 1–10 min | TBD | Local: negligible; IBM: per-shot. |
| Routing (RL) | &lt; 1 min | TBD | Local CPU. |
| Inverse design | 1–5 min | TBD | Depends on model and device. |
| Full pipeline (routing + inverse + HEaC + GDS) | 5–30 min | TBD | Local: CPU; add IBM if routing on hardware. |
| MEEP verify | 5–60 min | TBD | CPU-bound; scale with problem size. |
| Monte Carlo (N samples) | N × (single run) | TBD | Linear in N. |

**Action:** Instrument runs (task type, duration, backend) and optionally tag with project/circuit size. Fill this table with measured or estimated values; revisit after [ARCHITECTURE_MODULARIZATION_PROPOSAL.md](ARCHITECTURE_MODULARIZATION_PROPOSAL.md) (e.g. EKS workers) is in place.

---

## 3. Financial margin and budget guardrail

- **Need:** When running at scale (e.g. many users or many pipeline runs), we need a **financial margin assessment**: expected monthly or quarterly spend on IBM credits, EKS (if used), and any other cloud services vs. budget.
- **Guardrail:** Define a **budget cap** or **alert threshold** (e.g. per project or per month) so that runaway jobs or misconfiguration do not exceed acceptable spend. Implementation can be: billing alerts, per-user or per-org quotas, or queue limits.
- **Recommendation:** Instrument and measure actual cost (or proxy: run time × backend) before and after modularization; then set guardrails based on data.

---

## 4. References

- [dispatcher.py](../../src/backend/dispatcher.py) — Hybrid compute routing.
- [PIPELINE_METRICS.md](PIPELINE_METRICS.md) — Pipeline success rate and latency (operational metrics).
- [ARCHITECTURE_MODULARIZATION_PROPOSAL.md](ARCHITECTURE_MODULARIZATION_PROPOSAL.md) — Worker scaling and deployment.
