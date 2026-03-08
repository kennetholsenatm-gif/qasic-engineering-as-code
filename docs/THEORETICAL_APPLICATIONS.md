# Theoretical Applications of the Quantum ASIC

This document summarizes **theoretical applications** of the Quantum ASIC—the minimal 3-qubit linear topology and gate set (H, X, Z, CNOT) described in [QUANTUM_ASIC.md](QUANTUM_ASIC.md). It maps each concept to existing protocols, demos, and documentation in the repo.

## Quantum ASIC recap

| Resource | Specification |
|----------|----------------|
| **Qubits** | 3 (linear chain: 0 — 1 — 2) |
| **Gates** | H, X, Z, CNOT (optional Rx for tamper model) |
| **Protocols** | Teleportation, tamper-evident (Thief), bit commitment, 3-qubit bit-flip code, QKD (BB84, E91) |

See [QUANTUM_ASIC.md](QUANTUM_ASIC.md) for the full spec and [demos/demo_asic.py](../demos/demo_asic.py) to validate and run protocols on the ASIC.

## Protocol layer (implemented)

| Protocol | What it demonstrates | Code / demo |
|----------|----------------------|-------------|
| **Teleportation** | Bell pair creation, state transfer with classical message, no cloning | [protocols/teleportation.py](../protocols/teleportation.py), [demos/demo_teleport.py](../demos/demo_teleport.py) |
| **Tamper-evident (Thief)** | Intercepting the message disturbs the state; receiver sees fidelity drop | [protocols/tamper_evident.py](../protocols/tamper_evident.py), [demos/demo_thief.py](../demos/demo_thief.py) |
| **Bit commitment (toy)** | Commit to a bit using shared entanglement + classical reveal | [protocols/commitment.py](../protocols/commitment.py), [demos/demo_commitment.py](../demos/demo_commitment.py) |
| **3-qubit bit-flip code** | Minimal QEC: encode one logical qubit, correct one bit-flip error | [protocols/bitflip_code.py](../protocols/bitflip_code.py), [demos/demo_bitflip_code.py](../demos/demo_bitflip_code.py) |
| **QKD (BB84 / E91)** | Pedagogical prepare-and-measure and entanglement-based key distribution | [protocols/qkd.py](../protocols/qkd.py), [demos/demo_bb84.py](../demos/demo_bb84.py), [demos/demo_e91.py](../demos/demo_e91.py); [QKD.md](QKD.md) |
| **Quantum illumination (DV)** | Bell probe vs thermal loss channel, Chernoff comparison | [protocols/quantum_illumination.py](../protocols/quantum_illumination.py) |
| **Quantum radar (CV)** | TMSV + lossy thermal beam splitter, mutual info, SNR | [protocols/quantum_radar.py](../protocols/quantum_radar.py); [CV_QUANTUM_RADAR.md](CV_QUANTUM_RADAR.md) |

## Runnable applications (BQTC, qrnc)

| Application | Purpose | Doc |
|--------------|---------|-----|
| **BQTC** | Telemetry → Bayesian inference → Qiskit QUBO/QAOA path selection → VyOS BGP actuator | [APPLICATIONS.md](APPLICATIONS.md), [apps/bqtc/](../apps/bqtc/) |
| **qrnc** | Quantum-backed tokens (QRNG) and BitCommit-style two-party exchange | [APPLICATIONS.md](APPLICATIONS.md), [apps/qrnc/](../apps/qrnc/) |

## Theoretical extensions (data and control plane)

Conceptual uses of the same minimal ASIC in **data plane** (PHY/MAC, transmission security) and **control plane** (routing, policy, OAM) are described in [DATA_AND_CONTROL_PLANE_QUANTUM_ASIC.md](DATA_AND_CONTROL_PLANE_QUANTUM_ASIC.md). Summary:

| Concept | Domain | Building blocks in repo |
|---------|--------|-------------------------|
| **MACsec / tamper-evident tunneling** | Data plane | Tamper-evident protocol, teleportation topology |
| **Entanglement-assisted FEC** | Data plane | 3-qubit bit-flip code, [quantum-terrestrial-backhaul.md](quantum-terrestrial-backhaul.md) |
| **Ephemeral key streaming** | Data plane | BB84, E91, [protocols/qkd.py](../protocols/qkd.py) |
| **BGP route commitment** | Control plane | qrnc commitment/exchange, BitCommit-style primitive |
| **SD-WAN QAOA load balancing** | Control plane | BQTC pipeline, [engineering/routing_qubo_qaoa.py](../engineering/routing_qubo_qaoa.py) |
| **OAM fault localization (eavesdropping vs degradation)** | Control plane | Quantum illumination, quantum radar, BQTC actuator |

These are research/roadmap directions; the repo provides the protocol layer, simulation, and app building blocks.

## Further reading

- [APPLICATIONS.md](APPLICATIONS.md) — BQTC and qrnc run instructions and security caveats
- [DATA_AND_CONTROL_PLANE_QUANTUM_ASIC.md](DATA_AND_CONTROL_PLANE_QUANTUM_ASIC.md) — Full data/control plane narrative and code links
- [QUANTUM_ASIC.md](QUANTUM_ASIC.md) — ASIC spec and protocol mapping
- [WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.md](WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.md) — Vision, protocol layer, and hardware roadmap
