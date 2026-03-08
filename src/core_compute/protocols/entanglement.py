"""
Entanglement: Bell pair creation and conceptual "distribution".
Qubit convention: in 2-qubit state, qubit 0 = first (e.g. Alice), qubit 1 = second (e.g. Bob).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core_compute.state import State, bell_pair, product_state


def create_bell_pair(which: str = "Phi+") -> State:
    """Create a Bell pair |Φ⁺⟩ = (|00⟩ + |11⟩)/√2 (or Phi-, Psi+, Psi-)."""
    return bell_pair(which)


def distribute_pairs(n_pairs: int = 1, which: str = "Phi+") -> list[State]:
    """
    Conceptual: "distribution" of n_pairs Bell pairs.
    In a real setup this would be: source in space sends one photon to Alice, one to Bob.
    Here we just create n_pairs independent Bell states (each 2 qubits).
    """
    return [create_bell_pair(which) for _ in range(n_pairs)]


if __name__ == "__main__":
    bp = create_bell_pair()
    print("Bell pair (Phi+) state vector (4 amplitudes):")
    print(bp.vec.ravel())
    print("Expected: [0.707..., 0, 0, 0.707...] (|00⟩ + |11⟩)/√2")
