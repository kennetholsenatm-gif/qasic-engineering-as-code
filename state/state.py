"""
Minimal state-vector representation for n qubits.
States are complex column vectors of shape (2**n, 1); we enforce normalization.
"""
from __future__ import annotations

import numpy as np
from typing import Union

# Default dtype for state vectors
CDTYPE = np.complex128


class State:
    """State vector for n qubits: |ψ⟩ with shape (2**n, 1), normalized."""

    def __init__(self, data: np.ndarray, n_qubits: int | None = None):
        data = np.asarray(data, dtype=CDTYPE).reshape(-1, 1)
        if n_qubits is None:
            n_qubits = max(0, int(np.round(np.log2(data.size))))
        if data.size != 2**n_qubits:
            raise ValueError(f"State size {data.size} != 2**{n_qubits}")
        self._vec = data / np.linalg.norm(data)
        self._n = n_qubits

    @property
    def n_qubits(self) -> int:
        return self._n

    @property
    def vec(self) -> np.ndarray:
        return self._vec

    def copy(self) -> State:
        return State(self._vec.copy(), self._n)

    def apply(self, gate: np.ndarray, qubits: list[int]) -> State:
        """Apply a 2**len(qubits) x 2**len(qubits) gate to the given qubits (LSB = 0)."""
        return State(
            _apply_gate(self._vec, self._n, gate, qubits),
            self._n,
        )

    def fidelity(self, other: State) -> float:
        """|⟨ψ|φ⟩|². Both must have same n_qubits."""
        if self._n != other._n:
            raise ValueError("Mismatched qubit count")
        return float(np.abs(np.vdot(self._vec.ravel(), other._vec.ravel())) ** 2)

    def __repr__(self) -> str:
        return f"State(n={self._n}, vec=\n{self._vec})"


def _apply_gate(
    vec: np.ndarray, n: int, gate: np.ndarray, qubits: list[int]
) -> np.ndarray:
    """Apply gate (2**k x 2**k) to qubits; gate acts on qubits in order (qubits[0] = LSB of gate)."""
    gate = np.asarray(gate, dtype=CDTYPE)
    k = len(qubits)
    if gate.shape != (2**k, 2**k):
        raise ValueError(f"Gate shape {gate.shape} not (2**{k}, 2**{k})")
    vec = vec.ravel()
    out = np.zeros_like(vec)
    size = 2**n
    for i in range(size):
        # Decompose i into bits: i = ... b_qubits[0] ... b_qubits[k-1] ...
        # Gate index: (b_qubits[0], ..., b_qubits[k-1]) -> row, col
        bits = [(i >> q) & 1 for q in qubits]
        row = sum(b << j for j, b in enumerate(bits))
        for col in range(2**k):
            j = i
            for idx, q in enumerate(qubits):
                if (col >> idx) & 1:
                    j |= 1 << q
                else:
                    j &= ~(1 << q)
            out[i] += gate[row, col] * vec[j]
    return out.reshape(-1, 1)


def ket0() -> State:
    return State(np.array([1, 0], dtype=CDTYPE).reshape(-1, 1), 1)


def ket1() -> State:
    return State(np.array([0, 1], dtype=CDTYPE).reshape(-1, 1), 1)


def product_state(*kets: Union[State, str]) -> State:
    """|a⟩⊗|b⟩⊗... from State objects or '0'/'1' strings."""
    vecs = []
    for k in kets:
        if isinstance(k, State):
            vecs.append(k._vec.ravel())
        elif k == "0":
            vecs.append(np.array([1, 0], dtype=CDTYPE))
        elif k == "1":
            vecs.append(np.array([0, 1], dtype=CDTYPE))
        else:
            raise ValueError(f"Unknown ket: {k}")
    out = vecs[0]
    for v in vecs[1:]:
        out = np.kron(out, v)
    return State(out.reshape(-1, 1), len(vecs))


def bell_pair(which: str = "Phi+") -> State:
    """Bell state on 2 qubits. which in Phi+, Phi-, Psi+, Psi-."""
    from . import gates

    s = product_state("0", "0")
    s = s.apply(gates.H, [0]).apply(gates.CNOT, [0, 1])
    if which == "Phi+":
        return s
    if which == "Phi-":
        return s.apply(np.array([[1, 0], [0, -1]], dtype=CDTYPE), [1])  # Z on 1
    if which == "Psi+":
        return s.apply(np.array([[0, 1], [1, 0]], dtype=CDTYPE), [1])  # X on 1
    if which == "Psi-":
        return s.apply(
            np.array([[0, -1], [1, 0]], dtype=CDTYPE), [1]
        )  # -iY on 1 -> Psi-
    raise ValueError(f"Unknown Bell state: {which}")
