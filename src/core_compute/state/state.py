"""
State-vector and density-matrix representation for n qubits, backed by QuTiP.
States are normalized; kets have shape (2**n, 1). Density matrices (rho) supported
for open-system fidelity. Gate application uses QuTiP tensor product and unitary evolution.
"""
from __future__ import annotations

from typing import Union

import numpy as np
import qutip as qt

# Default dtype for state vectors
CDTYPE = np.complex128

# QuTiP uses tensor(..., q0) so that q0 is LSB (fastest varying). Our qubit index 0 is LSB.
# So we store state as Qobj with dims [[2]*n, [1]*n] and data matching our vec (index = sum b_q * 2^q).


def _np_to_qobj_ket(vec: np.ndarray, n: int) -> qt.Qobj:
    """Convert our ket (2**n, 1) to QuTiP Qobj. Same index convention: qubit 0 LSB."""
    vec = np.asarray(vec, dtype=CDTYPE).ravel()
    if vec.size != 2**n:
        raise ValueError(f"State size {vec.size} != 2**{n}")
    vec = vec / np.linalg.norm(vec)
    dims = [[2] * n, [1] * n]
    return qt.Qobj(vec.reshape(-1, 1), dims=dims)


def _np_to_qobj_oper(rho: np.ndarray, n: int) -> qt.Qobj:
    """Convert density matrix (2**n, 2**n) to QuTiP Qobj."""
    rho = np.asarray(rho, dtype=CDTYPE)
    if rho.shape != (2**n, 2**n):
        raise ValueError(f"Rho shape {rho.shape} not (2^{n}, 2^{n})")
    tr = np.trace(rho).real
    if abs(tr) < 1e-14:
        raise ValueError("Density matrix has zero trace")
    rho = rho / tr
    dims = [[2] * n, [2] * n]
    return qt.Qobj(rho, dims=dims)


def _qobj_to_np_ket(q: qt.Qobj) -> np.ndarray:
    """Extract (2**n, 1) column vector from ket Qobj."""
    return np.asarray(q.full(), dtype=CDTYPE).reshape(-1, 1)


def _embed_gate(gate: np.ndarray, qubits: list[int], n: int) -> qt.Qobj:
    """
    Embed a 2**k x 2**k gate (acting on our qubits in order, qubits[0]=LSB) into full n-qubit space.
    Builds the full 2^n x 2^n unitary so arbitrary qubit indices are supported.
    """
    gate = np.asarray(gate, dtype=CDTYPE)
    k = len(qubits)
    if gate.shape != (2**k, 2**k):
        raise ValueError(f"Gate shape {gate.shape} not (2**{k}, 2**{k})")
    size = 2**n
    U_full = np.zeros((size, size), dtype=CDTYPE)
    for i in range(size):
        bits_i = [(i >> q) & 1 for q in qubits]
        row_g = sum(b << j for j, b in enumerate(bits_i))
        for col_g in range(2**k):
            j = i
            for idx, q in enumerate(qubits):
                if (col_g >> idx) & 1:
                    j |= 1 << q
                else:
                    j &= ~(1 << q)
            U_full[j, i] = gate[row_g, col_g]
    dims = [[2] * n, [2] * n]
    return qt.Qobj(U_full, dims=dims)


class State:
    """
    State vector or density matrix for n qubits, backed by QuTiP Qobj.
    Pure states: |ψ⟩ with shape (2**n, 1). Mixed states: ρ (2**n x 2**n).
    """

    def __init__(
        self,
        data: np.ndarray | qt.Qobj,
        n_qubits: int | None = None,
    ):
        if isinstance(data, qt.Qobj):
            self._qobj = data.copy()
            dims = data.dims[0]
            self._n = len(dims)
            if dims != [2] * self._n:
                raise ValueError("Qobj must be for qubits (dims [2]*n)")
            if data.type == "ket":
                self._is_mixed = False
            elif data.type == "oper":
                self._is_mixed = True
            else:
                raise ValueError("Qobj must be ket or oper")
            return

        data = np.asarray(data, dtype=CDTYPE)
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        if data.ndim == 2 and data.shape[0] == data.shape[1]:
            # Density matrix
            if n_qubits is None:
                n_qubits = max(0, int(np.round(np.log2(data.shape[0]))))
            self._n = n_qubits
            self._qobj = _np_to_qobj_oper(data, self._n)
            self._is_mixed = True
            return

        # Ket
        data = data.reshape(-1, 1)
        if n_qubits is None:
            n_qubits = max(0, int(np.round(np.log2(data.size))))
        if data.size != 2**n_qubits:
            raise ValueError(f"State size {data.size} != 2**{n_qubits}")
        self._n = n_qubits
        self._qobj = _np_to_qobj_ket(data, self._n)
        self._is_mixed = False

    @property
    def n_qubits(self) -> int:
        return self._n

    @property
    def is_pure(self) -> bool:
        return not self._is_mixed

    @property
    def vec(self) -> np.ndarray:
        """Ket as column vector (2**n, 1). For mixed state, returns dominant eigenvector as ket."""
        if self._is_mixed:
            # Return flattened diagonal or best pure approximation for backward compat
            rho = self._qobj.full()
            w, v = np.linalg.eigh(rho)
            i = np.argmax(w)
            return np.asarray(v[:, i], dtype=CDTYPE).reshape(-1, 1)
        return _qobj_to_np_ket(self._qobj)

    def copy(self) -> State:
        return State(self._qobj.copy(), n_qubits=self._n)

    def apply(self, gate: np.ndarray, qubits: list[int]) -> State:
        """
        Apply a 2**len(qubits) x 2**len(qubits) gate to the given qubits.
        Qubits are in LSB order (qubits[0] = LSB of gate). Uses QuTiP tensor embedding.
        """
        U = _embed_gate(gate, qubits, self._n)
        if self._is_mixed:
            new_rho = U * self._qobj * U.dag()
            return State(new_rho, n_qubits=self._n)
        new_ket = (U * self._qobj).unit()
        return State(new_ket, n_qubits=self._n)

    def fidelity(self, other: State) -> float:
        """
        Fidelity: pure-pure |⟨ψ|φ⟩|²; pure-mixed ⟨ψ|ρ|ψ⟩; mixed-mixed (Tr sqrt(...))².
        Both must have same n_qubits.
        """
        if self._n != other._n:
            raise ValueError("Mismatched qubit count")
        return float(qt.metrics.fidelity(self._qobj, other._qobj))

    def __repr__(self) -> str:
        return f"State(n={self._n}, pure={self.is_pure})"

    @classmethod
    def from_density(cls, rho: np.ndarray, n_qubits: int | None = None) -> State:
        """Construct State from a density matrix (2**n x 2**n)."""
        rho = np.asarray(rho, dtype=CDTYPE)
        if n_qubits is None:
            n_qubits = max(0, int(np.round(np.log2(rho.shape[0]))))
        return cls(rho, n_qubits=n_qubits)


def ket0() -> State:
    return State(qt.basis(2, 0), n_qubits=1)


def ket1() -> State:
    return State(qt.basis(2, 1), n_qubits=1)


def product_state(*kets: Union[State, str]) -> State:
    """|a⟩⊗|b⟩⊗... from State objects or '0'/'1' strings. Qubit 0 = LSB (rightmost)."""
    if len(kets) == 0:
        raise ValueError("product_state requires at least one ket")
    qobjs = []
    for k in kets:
        if isinstance(k, State):
            qobjs.append(k._qobj)
        elif k == "0":
            qobjs.append(qt.basis(2, 0))
        elif k == "1":
            qobjs.append(qt.basis(2, 1))
        else:
            raise ValueError(f"Unknown ket: {k}")
    # tensor( first, ..., last ) so last is LSB = our qubit 0
    full = qt.tensor(qobjs).unit()
    return State(full, n_qubits=len(qobjs))


def bell_pair(which: str = "Phi+") -> State:
    """Bell state on 2 qubits. which in Phi+, Phi-, Psi+, Psi-."""
    from . import gates

    s = product_state("0", "0")
    s = s.apply(gates.H, [0]).apply(gates.CNOT, [0, 1])
    if which == "Phi+":
        return s
    if which == "Phi-":
        return s.apply(np.array([[1, 0], [0, -1]], dtype=CDTYPE), [1])
    if which == "Psi+":
        return s.apply(np.array([[0, 1], [1, 0]], dtype=CDTYPE), [1])
    if which == "Psi-":
        return s.apply(
            np.array([[0, -1], [1, 0]], dtype=CDTYPE), [1]
        )
    raise ValueError(f"Unknown Bell state: {which}")
