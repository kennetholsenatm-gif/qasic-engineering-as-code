"""
Demo: quantum teleportation. Send an unknown state from Alice to Bob using
one Bell pair and two classical bits. Fidelity should be 1.0.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
from state import State, ket0, ket1
from protocols.teleportation import teleport, teleport_circuit


def main():
    print("=== Quantum teleportation demo ===\n")

    # Test with |0⟩, |1⟩, and a superposition
    tests = [
        ("|0>", ket0()),
        ("|1>", ket1()),
        ("|+> = (|0>+|1>)/sqrt(2)", State(np.array([1, 1], dtype=np.complex128).reshape(-1, 1) / np.sqrt(2), 1)),
        ("random a|0>+b|1>", State(np.array([0.6, 0.8], dtype=np.complex128).reshape(-1, 1), 1)),
    ]
    for name, msg in tests:
        received = teleport(msg)
        fid = msg.fidelity(received)
        print(f"  {name}: fidelity = {fid:.6f}  (expect 1.0)")
    print("\nTeleportation preserves the unknown state; no cloning occurred.\n")


if __name__ == "__main__":
    main()
