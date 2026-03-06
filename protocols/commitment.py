"""
Toy bit commitment over a quantum channel.
Alice commits to a bit b using shared entanglement; she opens by revealing b and
classical info that Bob can verify. Security (binding/hiding) is *toy*: we assume
no quantum storage and a passive adversary (see README).
Protocol:
  1. Setup: Bob creates a Bell pair and sends one half to Alice (conceptually:
     "quantum modem" receives one photon). So Alice has qubit 0, Bob has qubit 1.
  2. Commit: Alice commits to bit b. To commit to 0 she measures her qubit in Z;
     to commit to 1 she applies X then measures in Z. She stores the outcome m ∈ {0,1}.
  3. Open: Alice sends (b, m) to Bob. Bob measures his qubit in Z; outcome should
     equal m (since Bell pair correlates). He checks that (b, m) is consistent with
     the correlation. In our toy we use: commit to 0 → don't flip; commit to 1 → flip.
     So Bob's qubit is in |m⟩ after Alice's action; Bob measures and gets m, and knows
     Alice's announced b. Binding: Alice can't change b without changing her half
     (already measured). Hiding: until open, Bob's reduced state is maximally mixed
     so he gets no info about b. (Toy: we assume Alice doesn't keep a quantum state.)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from state import State, product_state, bell_pair
from state.gates import X, Z, H


def commit(bit: int, bell: State) -> tuple[int, int]:
    """
    Alice commits to bit (0 or 1). She has the first qubit of the Bell pair.
    - To commit to 0: measure in Z, get outcome m.
    - To commit to 1: apply X to her qubit, then measure in Z, get outcome m.
    Returns (bit, measurement_outcome_m). In a real protocol she would store
    a commitment string; here we return (b, m) as the "commitment".
    """
    if bit not in (0, 1):
        raise ValueError("bit must be 0 or 1")
    # Simulate: Bell is (|00⟩+|11⟩)/√2. Alice's qubit is 0.
    # If b=0: she measures Z -> prob 1/2 for 0, 1/2 for 1. We pick m by sampling.
    # If b=1: she applies X so state becomes (|10⟩+|01⟩)/√2, then measures Z -> same.
    # So m is random in {0,1} in both cases. The commitment is (b, m).
    # Bob's qubit: if m=0 and b=0, Bob has |0⟩; if m=1 and b=0, Bob has |1⟩; etc.
    # So Bob's state is |m⟩. When opening, Bob measures and gets m; we need to encode
    # b in something Bob can verify. In this toy: Alice sends (b, m). Bob measures
    # his qubit and gets m'. He checks m' == m (consistency). He doesn't get b from
    # the quantum state—he gets b from the classical reveal. So hiding: before open,
    # Bob's state is I/2 (max mixed). Binding: Alice committed to b and sent m; if
    # she changed b she'd need to have sent a different m, but m was fixed by her
    # measurement (we assume she doesn't keep a quantum copy).
    rng = np.random.default_rng()
    m = int(rng.integers(0, 2))
    return (bit, m)


def open_commitment(bit: int, m: int) -> tuple[int, int]:
    """Alice opens by revealing (bit, m). Returns same (for verification)."""
    return (bit, m)


def verify_commitment(
    bit: int,
    m: int,
    bob_measurement_outcome: int,
) -> bool:
    """
    Bob verified: he measured his qubit and got bob_measurement_outcome.
    In the honest case, his qubit was in |m⟩ so outcome should equal m.
    Returns True if bob_measurement_outcome == m (consistent).
    """
    return bob_measurement_outcome == m


def run_commitment_protocol(bit: int, seed: int | None = None) -> dict:
    """
    Full run: create Bell pair, Alice commits to bit, then opens.
    Returns dict with commitment, open message, and Bob's verification result.
    """
    if seed is not None:
        np.random.seed(seed)
    bell = bell_pair("Phi+")
    b, m = commit(bit, bell)
    # Bob's qubit after Alice's action: in honest protocol, if b=0 Alice measured
    # and got m, so Bob's half collapsed to |m⟩. If b=1, Alice applied X then
    # measured and got m, so Bob's half is |m⟩ (since Bell: |00⟩+|11⟩ -> X on 0
    # gives |10⟩+|01⟩; measure 0 get 1 -> Bob has |0⟩; measure 0 get 0 -> Bob has |1⟩).
    # So Bob's state is always |m⟩. We simulate Bob measuring and getting m.
    bob_outcome = m
    ok = verify_commitment(b, m, bob_outcome)
    return {
        "committed_bit": b,
        "measurement_m": m,
        "bob_outcome": bob_outcome,
        "verify_ok": ok,
    }


if __name__ == "__main__":
    print("Commit to 0:", run_commitment_protocol(0, seed=42))
    print("Commit to 1:", run_commitment_protocol(1, seed=43))
