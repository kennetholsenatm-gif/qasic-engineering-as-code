"""
Minimal density-matrix representation for n qubits (ρ as 2^n×2^n).
Used by the noise layer for the density-matrix path: channel application
ρ → Σ_i K_i ρ K_i† and fidelity F = ⟨ψ|ρ|ψ⟩ give exact average fidelity
over noise without sampling (no quantum trajectories).
Supports conversion to/from State and fidelity to a target pure state.
"""
from __future__ import annotations

import numpy as np
from typing import TYPE_CHECKING, Sequence

from .state import CDTYPE

if TYPE_CHECKING:
    from .state import State


def state_to_density(s: "State") -> np.ndarray:
    """Convert a pure State to its density matrix |ψ⟩⟨ψ| (shape 2^n x 2^n)."""
    v = np.asarray(s.vec, dtype=CDTYPE).ravel()
    return np.outer(v, v.conj())


def density_to_state(rho: np.ndarray, n_qubits: int | None = None) -> "State":
    """
    If rho is (approximately) rank-1, return the corresponding pure State.
    Otherwise returns the dominant eigenvector as a pure state (best pure approximation).
    """
    from .state import State

    rho = np.asarray(rho, dtype=CDTYPE)
    n = n_qubits if n_qubits is not None else max(0, int(np.round(np.log2(rho.shape[0]))))
    if rho.shape[0] != 2**n or rho.shape[1] != 2**n:
        raise ValueError("rho must be 2^n x 2^n")
    w, v = np.linalg.eigh(rho)
    i = np.argmax(w)
    return State(v[:, i].reshape(-1, 1), n)


def fidelity_pure_vs_density(target_pure: "State", rho: np.ndarray) -> float:
    """
    Fidelity between a pure state |ψ⟩ and a (possibly mixed) density matrix ρ:
    F = ⟨ψ|ρ|ψ⟩. Gives exact expectation value (no sampling). Same qubit count required.
    """
    from .state import State

    target_pure = target_pure.vec.ravel()  # (2^n,)
    rho = np.asarray(rho, dtype=CDTYPE)
    return float(np.real(np.vdot(target_pure, rho @ target_pure)))


class DensityState:
    """
    Density matrix for n qubits: ρ with shape (2^n, 2^n), Hermitian, positive, trace 1.
    Used in the noise layer to apply channels and compute exact average fidelity.
    """

    def __init__(self, data: np.ndarray, n_qubits: int | None = None):
        data = np.asarray(data, dtype=CDTYPE)
        if data.ndim != 2 or data.shape[0] != data.shape[1]:
            raise ValueError("Density matrix must be square")
        n = n_qubits if n_qubits is not None else max(0, int(np.round(np.log2(data.shape[0]))))
        if data.shape[0] != 2**n:
            raise ValueError(f"Density matrix size {data.shape[0]} != 2^{n}")
        # Normalize trace to 1
        tr = np.trace(data)
        if np.abs(tr) < 1e-14:
            raise ValueError("Density matrix has zero trace")
        self._rho = data / tr
        self._n = n

    @property
    def n_qubits(self) -> int:
        return self._n

    @property
    def rho(self) -> np.ndarray:
        return self._rho

    def copy(self) -> DensityState:
        return DensityState(self._rho.copy(), self._n)

    def apply_channel(self, qubit: int, kraus_ops: Sequence[np.ndarray]) -> DensityState:
        """Apply a single-qubit channel (Kraus ops) to the given qubit: ρ → Σ_i K_i ρ K_i†."""
        from .channels import apply_single_qubit_channel
        out = apply_single_qubit_channel(self._rho, qubit, kraus_ops, self._n)
        return DensityState(out, self._n)

    def apply_gate(self, gate: np.ndarray, qubits: list[int]) -> DensityState:
        """Apply unitary U to qubits: ρ → U ρ U†. Uses full unitary on 2^n space."""
        n = self._n
        gate = np.asarray(gate, dtype=CDTYPE)
        k = len(qubits)
        if gate.shape != (2**k, 2**k):
            raise ValueError(f"Gate shape {gate.shape} not (2^{k}, 2^{k})")
        dim = 2**n
        U_full = np.zeros((dim, dim), dtype=CDTYPE)
        for i in range(dim):
            bits_i = [(i >> q) & 1 for q in qubits]
            col = sum(b << idx for idx, b in enumerate(bits_i))
            for ki in range(2**k):
                ip = i
                for idx, q in enumerate(qubits):
                    if (ki >> idx) & 1:
                        ip |= 1 << q
                    else:
                        ip &= ~(1 << q)
                row = ki
                U_full[ip, i] = gate[row, col]
        out = U_full @ self._rho @ U_full.conj().T
        return DensityState(out, n)

    def fidelity_to_pure(self, target: "State") -> float:
        """Fidelity ⟨ψ|ρ|ψ⟩ between this density matrix and pure state |ψ⟩."""
        if target.n_qubits != self._n:
            raise ValueError("Mismatched qubit count")
        return fidelity_pure_vs_density(target, self._rho)

    @classmethod
    def from_state(cls, s: "State") -> DensityState:
        """Construct DensityState from a pure State."""
        return cls(state_to_density(s), s.n_qubits)

    def __repr__(self) -> str:
        return f"DensityState(n={self._n}, dim={self._rho.shape[0]})"
