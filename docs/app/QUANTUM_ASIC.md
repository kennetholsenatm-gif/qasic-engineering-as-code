# Quantum ASIC: Minimal Gates and Topology

Concept: **simplify quantum hardware to the minimum** needed for the toy protocols—teleportation, tamper-evidence, and bit commitment. One fixed topology and a small gate set, like an ASIC that only implements the circuits we care about.

**Pipeline vs reference spec:** The **pipeline** (OpenQASM → ASIC) accepts **any OpenQASM 2 or 3 file and any qubit count** and derives topology from the circuit's interaction graph. This document describes the **reference/demo** minimal spec (3 qubits, linear chain, minimal gate set) used in demos and protocol validation; it is not a limit on pipeline input.

## Spec summary

| Resource | Specification |
|----------|----------------|
| **Qubits** | 3 (reference/demo). Pipeline: any qubit count; topology from circuit. |
| **Topology** | Linear chain: `0 — 1 — 2`. Only adjacent pairs can interact. (This table = reference/demo spec.) |
| **1-qubit gates** | H, X, Z. Optional: Rx(θ) for tamper model. |
| **2-qubit gates** | CNOT only, on edges (0,1) or (1,2). |

No all-to-all connectivity, no SWAP, no T or other universal gates. Not universal quantum computation—just enough for these protocols.

## Topology (ASCII)

```
  [0] ----- [1] ----- [2]
   msg    Alice      Bob
          Bell       Bell
```

- **Teleport:** Qubits 0 (message), 1 (Alice’s Bell half), 2 (Bob’s Bell half). Gates: H(1), CNOT(1,2), CNOT(0,1), H(0). Bob’s X/Z corrections are classical.
- **Commitment:** Qubits 0 (Alice), 1 (Bob). Bell creation: H(0), CNOT(0,1). Commit-to-1: X(0). Measurements are classical.
- **Thief:** Teleport circuit plus Rx(θ) on qubit 2 (disturbance on Bob’s qubit).

## Gate set (minimal)

- **H** – Hadamard (superposition).
- **X** – bit flip.
- **Z** – phase flip.
- **CNOT** – control-not, only on (0,1) or (1,2).
- **Rx(θ)** – optional; rotation about X for tamper-evidence demo.

No Y, no T, no Toffoli. This is intentionally not universal.

## Protocol → ASIC mapping

| Protocol | ASIC ops (in order) |
|----------|----------------------|
| Teleport | H(1), CNOT(1,2), CNOT(0,1), H(0) |
| Commitment (Bell) | H(0), CNOT(0,1) |
| Thief | Teleport ops + Rx(θ)(2) |

All of these validate against the same topology and gate set.

## Why this is useful

- **Hardware design:** A real “quantum modem” or link could be built with only these gates and a linear nearest-neighbour layout—no full connectivity.
- **Verification:** Circuits are checked so that only allowed gates on allowed edges are used.
- **Extensibility:** Adding a new protocol means adding a new op list and checking it fits the same ASIC; if not, the spec (qubits, edges, or gates) can be extended minimally.

## Connection to metasurface quantum bus

In the expanded whitepaper (**[WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.md](WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.md)**), the metasurface is proposed as a *reconfigurable* quantum bus. The Quantum ASIC’s minimal topology and gate set are the **protocol-layer specification** that such a bus can be programmed to realize—without adding physical wires—from on-chip entanglement to over-the-air secure SATCOM.

## Code

- `asic/qasm_loader.py` – load OpenQASM 2.0 or 3.0 (when `qiskit-qasm3-import` is installed), map to ASIC ops; optional decomposition to H, X, Z, Rx, CNOT. See [OPENQASM_TO_ASIC_PIPELINE.md](OPENQASM_TO_ASIC_PIPELINE.md) for the full QASM → ASIC chain and pain points.
- `asic/topology.py` – qubit count and edges.
- `asic/gate_set.py` – allowed gate names (and parametrized Rx).
- `asic/circuit.py` – `Op` dataclass, `validate_circuit()`, `protocol_*_ops()`.
- `asic/executor.py` – run a list of `Op` on the simulator `State`.
- `demos/demo_asic.py` – validate all protocol circuits and run teleport on the ASIC.
