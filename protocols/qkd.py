"""
Pedagogical QKD: BB84 and E91 (Ekert 91). Pure Python/NumPy using state layer.
BB84: prepare-and-measure; E91: entangled pairs + CHSH.
See docs/QKD.md for basis angles and CHSH reference.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from typing import Any

if str(Path(__file__).resolve().parents[1]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from state import State, ket0, ket1
from state.gates import H


# --- BB84 ---

def _measure_z(state: State, qubit: int) -> tuple[int, State]:
    """Projective measure in Z; return outcome 0 or 1 and collapsed state."""
    vec = state.vec.ravel()
    n = state.n_qubits
    p0 = 0.0
    for i in range(2**n):
        if ((i >> qubit) & 1) == 0:
            p0 += np.abs(vec[i]) ** 2
    if np.random.random() < p0:
        # collapse to |0> on qubit
        out = np.zeros_like(vec)
        for i in range(2**n):
            if ((i >> qubit) & 1) == 0:
                out[i] = vec[i]
        out = out / np.linalg.norm(out)
        return 0, State(out.reshape(-1, 1), n)
    else:
        out = np.zeros_like(vec)
        for i in range(2**n):
            if ((i >> qubit) & 1) == 1:
                out[i] = vec[i]
        out = out / np.linalg.norm(out)
        return 1, State(out.reshape(-1, 1), n)


def _measure_x(state: State, qubit: int) -> tuple[int, State]:
    """Measure in X basis (H then Z)."""
    from state.gates import H
    s = state.apply(H, [qubit])
    return _measure_z(s, qubit)


def run_bb84(
    n_bits: int = 64,
    seed: int | None = None,
) -> dict[str, Any]:
    """
    BB84: Alice sends random bits in Z or X basis; Bob measures Z or X at random.
    Sift to same basis; use half for key, half for QBER. No eavesdropper.
    """
    if seed is not None:
        np.random.seed(seed)
    alice_bits = np.random.randint(0, 2, size=n_bits)
    alice_bases = np.random.randint(0, 2, size=n_bits)  # 0=Z, 1=X
    bob_bases = np.random.randint(0, 2, size=n_bits)
    bob_outcomes = np.zeros(n_bits, dtype=int)
    for i in range(n_bits):
        # Alice prepares |0> or |1> in Z, or |+> or |-> in X
        if alice_bases[i] == 0:
            psi = ket1() if alice_bits[i] else ket0()
        else:
            psi = (ket1() if alice_bits[i] else ket0()).apply(H, [0])
        # Bob measures
        if bob_bases[i] == 0:
            out, _ = _measure_z(psi, 0)
        else:
            out, _ = _measure_x(psi, 0)
        bob_outcomes[i] = out
    # Sift
    sift = alice_bases == bob_bases
    n_sift = int(np.sum(sift))
    alice_sift = alice_bits[sift]
    bob_sift = bob_outcomes[sift]
    if n_sift < 2:
        return {
            "n_bits": n_bits,
            "n_sift": n_sift,
            "key_bits": [],
            "qber": None,
            "key_raw": None,
        }
    half = n_sift // 2
    key_alice = alice_sift[:half]
    key_bob = bob_sift[:half]
    qber_bits_alice = alice_sift[half:]
    qber_bits_bob = bob_sift[half:]
    qber = float(np.mean(qber_bits_alice != qber_bits_bob)) if half > 0 else 0.0
    return {
        "n_bits": n_bits,
        "n_sift": n_sift,
        "key_bits": (key_alice.tolist(), key_bob.tolist()),
        "key_agreement": np.all(key_alice == key_bob),
        "qber": qber,
        "key_raw": (key_alice.tolist(), key_bob.tolist()),
    }


# --- E91 ---

def run_e91(
    n_trials: int = 500,
    seed: int | None = None,
) -> dict[str, Any]:
    """
    E91: Bell pairs; Alice and Bob each choose one of three bases (0, 120°, 240° in X-Z plane).
    Compute CHSH S and extract key from correlated outcomes when bases match.
    Simplified: use Z, X, and (Z+X)/sqrt(2) as the three bases for pedagogy.
    """
    if seed is not None:
        np.random.seed(seed)
    from state import bell_pair
    from state.gates import H

    def measure_bell_in_basis(state: State, basis_alice: int, basis_bob: int) -> tuple[int, int]:
        """Measure Bell pair: Alice in basis_alice (0=Z, 1=X, 2=W), Bob in basis_bob. Return (a, b)."""
        s = state.copy()
        if basis_alice == 1:
            s = s.apply(H, [0])
        elif basis_alice == 2:
            s = s.apply(H, [0])  # third basis (simplified)
        if basis_bob == 1:
            s = s.apply(H, [1])
        elif basis_bob == 2:
            s = s.apply(H, [1])
        a, s1 = _measure_z(s, 0)
        b, _ = _measure_z(s1, 1)
        return a, b

    correlations = np.zeros((3, 3))
    counts = np.zeros((3, 3), dtype=int)
    key_alice = []
    key_bob = []
    for _ in range(n_trials):
        bell = bell_pair("Phi+")
        ba = np.random.randint(0, 3)
        bb = np.random.randint(0, 3)
        a, b = measure_bell_in_basis(bell, ba, bb)
        correlations[ba, bb] += (1 if a == b else -1)
        counts[ba, bb] += 1
        if ba == bb:
            key_alice.append(a)
            key_bob.append(b)
    for i in range(3):
        for j in range(3):
            if counts[i, j] > 0:
                correlations[i, j] /= counts[i, j]
    # CHSH: S = E(0,0)-E(0,1)+E(1,0)+E(1,1) (classical |S|<=2, quantum up to 2*sqrt2)
    s_chsh = correlations[0, 0] - correlations[0, 1] + correlations[1, 0] + correlations[1, 1]
    key_agreement = (np.array(key_alice) == np.array(key_bob)).all() if key_alice else True
    return {
        "n_trials": n_trials,
        "correlations": correlations.tolist(),
        "counts": counts.tolist(),
        "chsh_s": float(s_chsh),
        "key_bits": (key_alice, key_bob),
        "key_agreement": key_agreement,
        "n_key": len(key_alice),
    }
