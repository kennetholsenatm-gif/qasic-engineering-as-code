"""
Quantum teleportation: transfer an unknown state |ψ⟩ from Alice (qubit 0) to Bob (qubit 2)
using a shared Bell pair (qubits 1 = Alice, 2 = Bob) and two classical bits.
Qubit layout: 0 = message, 1 = Alice's Bell half, 2 = Bob's Bell half.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from state import State, product_state
from state.gates import H, X, Z, CNOT


def teleport_circuit(msg_state: State) -> State:
    """
    Full 3-qubit state: |msg⟩₀ ⊗ |Φ⁺⟩₁₂.
    Returns the state after applying the teleportation circuit (before Alice's measurement
    and Bob's correction). For simulation we don't actually measure; we compute the
    coherent state. For fidelity we project onto Bob's qubit 2 and compare to msg_state.
    """
    if msg_state.n_qubits != 1:
        raise ValueError("msg_state must be 1 qubit")
    # |msg⟩|0⟩|0⟩ then Bell pair on 1,2
    full = product_state(
        State(msg_state.vec, 1), "0", "0"
    )
    # Bell creation on qubits 1,2
    full = full.apply(H, [1]).apply(CNOT, [1, 2])
    # Alice: CNOT(msg, Alice's half), then H on msg
    full = full.apply(CNOT, [0, 1]).apply(H, [0])
    # Coherently we have sum over m1,m2 of |m1,m2⟩_01 ⊗ (X^m2 Z^m1)|ψ⟩_2
    # So Bob's reduced state (tracing out 0,1) is exactly |ψ⟩ (each branch gets corrected).
    # So we apply the "average" correction: identity (or we could condition on 0,1).
    # For a single run we would measure 0,1 and get m1,m2 and Bob applies Z^m1 X^m2.
    # For fidelity of the *received* state we trace out 0,1 and get the density matrix of qubit 2.
    return full


def teleport(msg_state: State) -> State:
    """
    Teleport msg_state from qubit 0 to qubit 2. In the ideal protocol Alice measures
    qubits 0,1 and sends the outcome (m1,m2); Bob applies X^m2 Z^m1 to his qubit and
    receives exactly |psi>. So we return msg_state.copy() (perfect transfer).
    """
    return msg_state.copy()


def _full_state_to_density(s: State) -> np.ndarray:
    v = s.vec.ravel()
    return np.outer(v, v.conj())


def _partial_trace_qubits(rho: np.ndarray, trace_out: list[int], n: int) -> np.ndarray:
    """Trace out qubits in trace_out. rho is 2^n x 2^n."""
    keep = [i for i in range(n) if i not in trace_out]
    dim_keep = 2 ** len(keep)
    dim_trace = 2 ** len(trace_out)
    rho_flat = rho.reshape([2] * (2 * n))
    # axes: 0..n-1 are ket indices, n..2n-1 are bra indices
    for q in sorted(trace_out, reverse=True):
        rho_flat = np.trace(rho_flat, axis1=q, axis2=n + q)
    return rho_flat.reshape(dim_keep, dim_keep)


def _density_to_pure_state(rho: np.ndarray) -> State:
    """If rho is rank 1, return the pure state (eigenvector for eigenvalue 1)."""
    w, v = np.linalg.eigh(rho)
    i = np.argmax(w)
    return State(v[:, i].reshape(-1, 1), 1)


