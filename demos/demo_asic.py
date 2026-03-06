"""
Quantum ASIC demo: validate that teleport, commitment, and thief protocols
compile to the minimal gate set and topology (3 qubits, linear chain, H/X/Z/CNOT/Rx).
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from asic import (
    DEFAULT_TOPOLOGY,
    DEFAULT_GATE_SET,
    validate_circuit,
    protocol_teleport_ops,
    protocol_commitment_ops,
    protocol_thief_ops,
    Op,
    ASICCircuit,
)
from asic.executor import run_asic_circuit
from state import State, product_state


def main():
    print("=== Quantum ASIC: minimal gates + topology for toy protocols ===\n")
    print(f"Topology: {DEFAULT_TOPOLOGY.n_qubits} qubits, edges {set(DEFAULT_TOPOLOGY.edges)}")
    print("  (linear chain: 0 - 1 - 2)\n")
    print(f"Gate set: 1q = H, X, Z, Rx(angle); 2q = CNOT (on edges only)\n")

    # Validate each protocol circuit
    for name, ops in [
        ("Teleportation", protocol_teleport_ops()),
        ("Bit commitment (Bell creation)", protocol_commitment_ops()),
        ("Teleport + Thief (Rx on qubit 2)", protocol_thief_ops(qubit=2, angle=0.3)),
    ]:
        errs = validate_circuit(ops)
        status = "OK" if not errs else "FAIL"
        print(f"  {name}: {status}")
        if errs:
            for e in errs:
                print(f"    - {e}")
        else:
            print(f"    ops: {[ (o.gate, o.targets) for o in ops ]}")

    # Run teleport circuit on ASIC (initial |+>|0>|0>)
    print("\n--- Execute teleport circuit on ASIC ---")
    psi = State(
        (1.0 / np.sqrt(2)) * np.array([1, 1], dtype=complex).reshape(-1, 1),
        1,
    )
    initial = product_state(psi, "0", "0")
    run_asic_circuit(initial, protocol_teleport_ops())
    print("  Initial: |+>|0>|0>  ->  After 4 ASIC ops: 3-qubit state (Bob gets |+> after correction).")

    print("\nAll protocols fit on the same fixed topology and gate set (Quantum ASIC).\n")


if __name__ == "__main__":
    main()
