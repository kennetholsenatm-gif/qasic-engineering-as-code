# Applications

This directory hosts two applications integrated into QASIC Engineering-as-Code:

- **BQTC** — Bayesian-Quantum Traffic Controller
- **qrnc** — Quantum-Backed Tokens and BitCommit-Style Exchange

See [docs/APPLICATIONS.md](../docs/APPLICATIONS.md) for purpose, run instructions, and security caveats.

## BQTC (Bayesian-Quantum Traffic Controller)

Four-stage pipeline: **Telemetry (sFlow/NetFlow)** → **Bayesian inference** → **Qiskit QUBO path optimizer** → **VyOS BGP actuator**.

**Run:**

1. Install BQTC dependencies: `pip install -r apps/bqtc/requirements.txt`
2. Configure `apps/bqtc/config/topology.yaml` and `apps/bqtc/config/pipeline.yaml` (do not commit real device IPs or credentials; use environment variables for `IBM_QUANTUM_TOKEN` when using IBM hardware).
3. From repo root: `cd apps/bqtc && python pipeline.py`

The pipeline runs periodically (default 300 s); start VyOS sFlow/NetFlow export to this host (ports 6343 and 2055 by default).

## qrnc (Quantum-Backed Tokens and Exchange)

QRNC tokens are minted from quantum entropy (shared `QRNG.PY` at repo root). The package provides a BitCommit-style two-party exchange: commit then reveal.

**Run:**

From repo root (QRNG.PY must be at repo root):

```bash
python -c "from apps.qrnc import mint_qrnc, run_two_party_exchange; t = mint_qrnc(32, use_real_hardware=False); print(t.value[:16], '...')"
```

Run tests: `python -m pytest apps/qrnc/tests/ -v`

The web API (if enabled) exposes `POST /apps/qrnc/mint` and `POST /apps/qrnc/exchange`; see the main [README](../README.md) and [app/README.md](../app/README.md).
