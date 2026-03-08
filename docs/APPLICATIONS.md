# Applications: BQTC and QRNC

Two applications are integrated into QASIC Engineering-as-Code under `apps/`: **BQTC** (Bayesian-Quantum Traffic Controller) and **qrnc** (Quantum-Backed Tokens and BitCommit-Style Exchange). This document describes their purpose, how to run them, and security caveats.

## BQTC — Bayesian-Quantum Traffic Controller

**Purpose:** Four-stage pipeline for traffic control: ingest sFlow/NetFlow telemetry, run Bayesian inference to predict bandwidth demand, use a Qiskit QUBO (QAOA) optimizer to select paths per VNI, and apply decisions via a VyOS BGP actuator (dry-run by default).

**Pipeline stages:**

1. **Telemetry** — UDP collectors (sFlow port 6343, NetFlow 2055) and rolling buffer.
2. **Bayesian** — Features and model (sklearn or PyMC), inference to produce a bandwidth matrix.
3. **Quantum** — QUBO builder, QAOA solver (StatevectorSampler or IBM), path → BGP mapping.
4. **Actuator** — VyOS client (pyvyos/vymgmt), BGP policy, apply (or dry-run).

**How to run from QASIC:**

1. Install BQTC dependencies: `pip install -r apps/bqtc/requirements.txt`
2. Configure `apps/bqtc/config/topology.yaml` (leafs, paths, VNIs) and `apps/bqtc/config/pipeline.yaml` (ports, intervals, dry_run).
3. Start VyOS sFlow/NetFlow export to this host (ports 6343 and 2055 by default).
4. From repo root: `cd apps/bqtc && python pipeline.py`

The pipeline runs periodically (default 300 s). The Bayesian stage uses the last 10 minutes of flows; the actuator applies BGP local-preference (dry-run by default).

**Security and config caveats:**

- **Do not commit real device IPs or credentials.** Use environment variables for `IBM_QUANTUM_TOKEN` when using IBM hardware.
- BQTC config remains under `apps/bqtc/config/`; no merge with QASIC’s main config.

---

## qrnc — Quantum-Backed Tokens and BitCommit-Style Exchange

**Purpose:** QRNC tokens are minted from quantum entropy (via the shared `QRNG.PY` at the QASIC repo root). The package adds a BitCommit-style two-party exchange: commit then reveal, so neither party can change their token after seeing the other’s.

**Protocol (two-party):**

1. **Commit phase:** Alice and Bob each compute `H(token || nonce)` and exchange these commitments.
2. **Reveal phase:** Both send `(token, nonce)`. Each verifies the other’s pair against the commitment.
3. **Completion:** If both verifications pass, the swap is complete; optionally an `ExchangeRecord` is produced for a ledger.

**How to run from QASIC:**

- Ensure `QRNG.PY` is at the repo root (it is provided there for qrnc).
- From repo root:
  - Mint: `python -c "from apps.qrnc import mint_qrnc; t = mint_qrnc(32, use_real_hardware=False); print(t.value)"`
  - Exchange: use `run_two_party_exchange(token_a, token_b, party_a_id='Alice', party_b_id='Bob')` (see `apps/qrnc/README.md`).
- Run tests: `python -m pytest apps/qrnc/tests/ -v`

**Security caveats (exploratory):**

- **No unconditional security.** Quantum bit commitment cannot be unconditionally secure (Mayers–Lo–Chau). This design uses a **classical** hash commitment for the exchange; the quantum part is token **generation** only.
- **Binding:** Hash-based commitment is computationally binding (collision resistance of SHA-256).
- **Hiding:** Hiding relies on sufficient entropy in token and nonce; nonce must be fresh and secret until reveal.
- **Scope:** No authentication, network layer, or replay protection in this iteration. The protocol only prevents one party from changing their token after seeing the other’s; it does not protect against DoS or transport issues.

---

## Shared QRNG

`QRNG.PY` at the QASIC repo root is used by **qrnc** for minting. It uses Qiskit (StatevectorSampler for simulation; optional IBM Runtime for real hardware). BQTC does not require this file for its main pipeline; it is provided once at repo root for qrnc.
