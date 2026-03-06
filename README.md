# Toy Quantum Protocols

Pedagogical implementations of **quantum teleportation**, **tamper-evident channels**, and **bit commitment** over a quantum link. Inspired by space-based entanglement distribution and "quantum modem" ideas—all in pure Python with NumPy.

## Concepts

| Protocol | What it demonstrates |
|----------|----------------------|
| **Entanglement & teleportation** | Bell pair creation, state transfer with classical message, no cloning. |
| **Tamper-evidence (Thief)** | Intercepting the "message" disturbs the state; receiver sees fidelity drop. |
| **Toy bit commitment** | Commit to a bit using shared entanglement + classical reveal; security relies on tamper-evident channel + bounded storage (toy assumptions). |

## Security assumptions (toy)

- **No unconditional security.** The bit-commitment toy is *not* information-theoretically secure (Mayers–Lo–Chau no-go applies in the full model). We assume a **passive** adversary or **bounded quantum storage** so the protocol is binding/hiding in a pedagogical setting.
- **Perfect devices.** No channel loss, no detector noise—we're illustrating principles.

## Quantum ASIC

The **Quantum ASIC** idea: reduce hardware to **only the gates and topology** needed for these protocols—no full connectivity, no universal gate set. One fixed “chip” spec:

- **3 qubits**, linear chain: `0 — 1 — 2` (only adjacent pairs can do CNOT).
- **Gates:** H, X, Z, CNOT (and optional Rx for the tamper model).

All three protocols compile to this minimal set and validate against it. See **[docs/QUANTUM_ASIC.md](docs/QUANTUM_ASIC.md)** for the spec and **`python demos/demo_asic.py`** to validate and run.

## Project layout

```
toy-quantum-protocols/
├── README.md
├── requirements.txt
├── docs/
│   └── QUANTUM_ASIC.md       # ASIC spec: topology + gate set
├── state/                    # Minimal qubit simulation
│   ├── __init__.py
│   ├── state.py              # State vectors, ket notation
│   └── gates.py              # I, H, X, Z, CNOT, etc.
├── asic/                     # Quantum ASIC: minimal gates + topology
│   ├── __init__.py
│   ├── topology.py           # Qubit count, allowed edges
│   ├── gate_set.py           # Allowed 1q/2q gates
│   ├── circuit.py            # Op list, validation, protocol_*_ops()
│   └── executor.py           # Run ASIC circuit on State
├── protocols/                # Protocol logic
│   ├── __init__.py
│   ├── entanglement.py       # Bell pairs, distribution
│   ├── teleportation.py      # Teleport one qubit
│   ├── tamper_evident.py     # Thief intercept → fidelity drop
│   └── commitment.py         # Toy bit commitment
├── engineering/               # Metasurface routing + inverse design (optional)
│   ├── README.md
│   ├── requirements-engineering.txt
│   ├── routing_qubo_qaoa.py  # QUBO: logical qubits -> physical nodes (QAOA/classical)
│   └── metasurface_inverse_net.py  # PyTorch: target topology -> phase profile
└── demos/                    # Runnable scripts
    ├── demo_teleport.py
    ├── demo_thief.py
    ├── demo_commitment.py
    └── demo_asic.py          # Validate protocols on ASIC, run teleport
```

## Quick start

```bash
cd toy-quantum-protocols
pip install -r requirements.txt
python demos/demo_teleport.py
python demos/demo_thief.py
python demos/demo_commitment.py
python demos/demo_asic.py     # Quantum ASIC: gates + topology
```

## Whitepaper

**[Holographic Metasurfaces as a Scalable Control Layer for Solid-State Quantum Entanglement and Secure SATCOM](docs/WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.md)** — Expanded whitepaper on using programmable metasurfaces as a cryogenic quantum bus (on-chip) and for weather-resilient, tamper-evident quantum SATCOM and phased-array quantum radar. Ties the protocol layer (minimal topology, Quantum ASIC) to the hardware vision.

## References

- [Quirk: Quantum Circuit Simulator](https://algassert.com/quirk) — e.g. teleportation + "Thief" circuit.
- Mayers–Lo–Chau: no-go for unconditional quantum bit commitment.
- Micius satellite: space-based entanglement distribution and teleportation.
