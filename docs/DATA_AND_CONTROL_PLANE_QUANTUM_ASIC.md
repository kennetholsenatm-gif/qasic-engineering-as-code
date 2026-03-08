# Data and Control Plane Quantum ASIC Extensions

This document describes **conceptual extensions** of the QASIC stack—minimal gate set, 3-qubit linear topology, tamper-evident channels, and hybrid QAOA optimization—to **Data Plane** (traffic forwarding, PHY/MAC layer, physical transmission security) and **Control Plane** (routing, policy, network orchestration) of advanced network infrastructures. These are roadmap and research directions; the existing repository provides the protocol, simulation, and application building blocks. Each concept below links to the relevant code paths (demos, protocols, apps) in the repo.

---

## Data Plane Applications

The data plane is responsible for the actual movement, encapsulation, and physical transmission of user packets. Low-qubit ASICs here would operate at the physical (PHY) or MAC layer.

| Concept | Description | Existing QASIC building blocks |
|--------|-------------|--------------------------------|
| **Quantum-Assisted MACsec / Inline Tamper-Evident Tunneling** | A low-qubit ASIC embedded in a NIC or optical/RF transceiver generates continuous streams of entangled pairs (using the 0–1–2 teleportation topology) synchronized with high-value packet flows. The data payload is classically encrypted; the packet header or a specialized trailer carries a quantum state measurement. If an adversary copies or mirrors the traffic, the entanglement breaks. The receiving ASIC detects the fidelity drop at line-rate and drops compromised frames before they are processed. | [protocols/tamper_evident.py](../protocols/tamper_evident.py), [demos/demo_thief.py](../demos/demo_thief.py), teleportation topology 0–1–2; [QUANTUM_ASIC.md](QUANTUM_ASIC.md). |
| **Minimalist Entanglement-Assisted FEC** | Radio links (e.g. terrestrial P2P backhaul) suffer from weather fade and multipath. A 3-qubit ASIC runs the 3-qubit bit-flip code continuously for the most critical bits (synchronization frames, high-priority URLLC traffic), providing ultra-low latency, hardware-level quantum error correction instead of heavy software-based FEC. | [demos/demo_bitflip_code.py](../demos/demo_bitflip_code.py), bit-flip code in [protocols/](../protocols/); [quantum-terrestrial-backhaul.md](quantum-terrestrial-backhaul.md). |
| **Ephemeral One-Time-Pad Key Streaming at Line Rate** | Using BB84 or E91 optimized for the minimal gate set, the ASIC acts as a dedicated key-streaming coprocessor. Instead of a CPU rotating IPsec or MACsec keys every hours or minutes, the low-qubit ASIC leverages the microwave link to negotiate symmetric keys continuously, providing a rotating cryptographic pad per-packet or per-frame without burdening classical routing hardware. | [demos/demo_bb84.py](../demos/demo_bb84.py), [demos/demo_e91.py](../demos/demo_e91.py); [protocols/qkd.py](../protocols/qkd.py). |

---

## Control Plane Applications

The control plane handles routing tables, link failure detection, and traffic engineering. Low-qubit ASICs here integrate with SDN controllers or routing protocols such as BGP.

| Concept | Description | Existing QASIC building blocks |
|--------|-------------|--------------------------------|
| **Quantum-Backed BGP Route Commitment** | BGP route hijacking (a malicious AS advertising a false path) is a major vulnerability. The BitCommit-style primitive can be extended to routing: when two AS edge routers peer, they use a low-qubit ASIC to generate a quantum commitment for their routing tables. The commitment is tamper-evident and binding, so a router cannot secretly alter advertised paths or spoof a path without breaking verification—enforcing cryptographic honesty in BGP updates. | [apps/qrnc/commitment.py](../apps/qrnc/commitment.py), [apps/qrnc/exchange.py](../apps/qrnc/exchange.py); [APPLICATIONS.md](APPLICATIONS.md) (qrnc). |
| **Real-Time QAOA for SD-WAN Dynamic Load Balancing** | A mesh of SD-WAN edge routers, each with a low-qubit ASIC, runs shallow-depth QAOA circuits locally. Instead of a centralized cloud optimizer, these routers execute distributed QUBO formulations (e.g. Max-Cut, TSP-like) to solve localized rebalancing. The network can rebalance traffic across multiple ISP links in milliseconds in response to micro-bursts. | [apps/bqtc/](../apps/bqtc/) (BQTC: telemetry → Bayesian → QUBO/QAOA → actuator); [engineering/routing_qubo_qaoa.py](../engineering/routing_qubo_qaoa.py); [APPLICATIONS.md](APPLICATIONS.md) (BQTC). |
| **OAM Fault Localization (Eavesdropping vs Natural Degradation)** | Differentiating natural signal degradation (e.g. rain fade on a SATCOM link) from active eavesdropping or jamming is difficult classically. The control plane can use the low-qubit ASIC to periodically send probe states (quantum illumination) across the network. Return statistics (Chernoff exponent, decoherence signature) distinguish atmospheric thermal noise from an active wiretap. On eavesdropper detection, the control plane’s BGP actuator triggers a localized routing policy to steer traffic away from the compromised link. | [protocols/quantum_illumination.py](../protocols/quantum_illumination.py), [protocols/quantum_radar.py](../protocols/quantum_radar.py); [CV_QUANTUM_RADAR.md](CV_QUANTUM_RADAR.md); BQTC actuator for policy response. |

---

## Implementation outlook

Realizing these extensions would require hardware integration (NIC/transceiver embedding, line-rate ASICs), control-plane APIs (SDN/BGP), and further research. This repository provides the protocol layer, simulation tools, and application examples (BQTC, qrnc, demos) that form the building blocks for such future data-plane and control-plane deployments.
