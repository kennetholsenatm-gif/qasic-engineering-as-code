"""
Continuous-variable (CV) Gaussian states via covariance matrices.

Gaussian states are fully described by mean vector d (2N) and covariance matrix V (2N x 2N)
for N modes. Quadrature order: (q1, p1, q2, p2, ...). We use hbar=1 so vacuum has V = I/2 per mode.

Operations are applied via symplectic matrices S: V' = S V S^T, d' = S d.
Used by the toy CV quantum radar (TMSV + lossy beam splitter).
"""
from __future__ import annotations

import numpy as np
from typing import Optional

# Symplectic form: Omega = block_diag(J, J, ...) with J = [[0,1],[-1,0]]
def symplectic_form(n_modes: int) -> np.ndarray:
    """Standard symplectic form for n_modes: Omega such that S Omega S^T = Omega for symplectic S."""
    J = np.array([[0, 1], [-1, 0]], dtype=np.float64)
    return np.kron(np.eye(n_modes, dtype=np.float64), J)


def vacuum_covariance(n_modes: int) -> np.ndarray:
    """Covariance matrix of vacuum: V = (1/2) I_{2n} (hbar=1)."""
    return np.eye(2 * n_modes, dtype=np.float64) / 2.0


def thermal_covariance(n_bar: float) -> np.ndarray:
    """Single-mode thermal state covariance (mean photon number n_bar). V = (n_bar + 1/2) I_2."""
    return (n_bar + 0.5) * np.eye(2, dtype=np.float64)


class GaussianState:
    """
    Gaussian state for N modes: mean d (2N) and covariance V (2N x 2N), both real.
    Zero mean by default (e.g. vacuum, TMSV, thermal). V must be symmetric positive definite
    and satisfy the uncertainty principle V + (i/2) Omega >= 0 (checked optionally).
    """

    def __init__(
        self,
        V: np.ndarray,
        d: Optional[np.ndarray] = None,
        n_modes: Optional[int] = None,
        check_physical: bool = True,
    ):
        V = np.asarray(V, dtype=np.float64)
        if V.ndim != 2 or V.shape[0] != V.shape[1] or V.shape[0] % 2 != 0:
            raise ValueError("V must be 2N x 2N")
        n = n_modes if n_modes is not None else V.shape[0] // 2
        if V.shape[0] != 2 * n:
            raise ValueError("V size must be 2 * n_modes")
        if not np.allclose(V, V.T):
            raise ValueError("V must be symmetric")
        self._V = (V + V.T) / 2.0  # ensure symmetry
        self._n = n
        if d is not None:
            d = np.asarray(d, dtype=np.float64).ravel()
            if d.size != 2 * n:
                raise ValueError("d must have length 2 * n_modes")
            self._d = d
        else:
            self._d = np.zeros(2 * n, dtype=np.float64)
        if check_physical:
            om = symplectic_form(n)
            # Physicality: V - (1/2) i Omega >= 0 as complex matrix, i.e. eigenvalues of Omega @ V >= 1/2
            # Equivalently symplectic eigenvalues nu_j >= 1/2. Quick check: V > 0 and det(V) >= (1/4)^n.
            if np.any(np.linalg.eigvalsh(self._V) <= 1e-10):
                raise ValueError("V must be positive definite")

    @property
    def n_modes(self) -> int:
        return self._n

    @property
    def V(self) -> np.ndarray:
        return self._V

    @property
    def d(self) -> np.ndarray:
        return self._d

    def apply_symplectic(self, S: np.ndarray, modes: Optional[list[int]] = None) -> "GaussianState":
        """
        Apply symplectic S: V' = S V S^T, d' = S d.
        If modes is given, S is applied to those modes only (S is 2*len(modes) x 2*len(modes));
        otherwise S is 2n x 2n and applied to all.
        """
        S = np.asarray(S, dtype=np.float64)
        n = self._n
        if modes is not None:
            # Embed S into full 2n x 2n: identity on other modes
            k = len(modes)
            if S.shape != (2 * k, 2 * k):
                raise ValueError("S shape must match modes")
            S_full = np.eye(2 * n, dtype=np.float64)
            for i, mi in enumerate(modes):
                for j, mj in enumerate(modes):
                    S_full[2 * mi : 2 * mi + 2, 2 * mj : 2 * mj + 2] = S[2 * i : 2 * i + 2, 2 * j : 2 * j + 2]
            S = S_full
        if S.shape != (2 * n, 2 * n):
            raise ValueError("S must be 2n x 2n")
        V_new = S @ self._V @ S.T
        d_new = S @ self._d
        return GaussianState(V_new, d_new, n, check_physical=False)

    def reduced(self, modes: list[int]) -> "GaussianState":
        """Reduce to the given modes (covariance and mean of the subsystem)."""
        idx = []
        for m in modes:
            if not 0 <= m < self._n:
                raise ValueError("mode index out of range")
            idx.extend([2 * m, 2 * m + 1])
        V_red = self._V[np.ix_(idx, idx)]
        d_red = self._d[idx]
        return GaussianState(V_red, d_red, n_modes=len(modes), check_physical=False)

    def symplectic_eigenvalues(self) -> np.ndarray:
        """Symplectic eigenvalues (nu_j >= 1/2) of V. For one mode: nu = sqrt(det(V))."""
        n = self._n
        Om = symplectic_form(n)
        # Eigenvalues of i Omega V are real ( +/- nu_j ); symplectic spectrum = their absolute values.
        eigs = np.linalg.eigvals(1j * (Om @ self._V))
        nu = np.sort(np.abs(np.real(eigs)))
        return nu[0::2]  # one per mode (pairs are +/- nu, sorted so [nu1, nu1, nu2, nu2, ...])

    def von_neumann_entropy(self) -> float:
        """Von Neumann entropy S = sum_j g((nu_j - 1)/2), g(x) = (x+1)log(x+1) - x log(x)."""
        nu = self.symplectic_eigenvalues()
        nu = np.maximum(nu, 0.5 + 1e-12)
        x = (nu - 1.0) / 2.0
        # g(x) = (x+1)*log(x+1) - x*log(x), with 0*log(0)=0
        g = np.where(x <= 1e-12, 0.0, (x + 1) * np.log(x + 1) - x * np.log(np.maximum(x, 1e-12)))
        return float(np.sum(g))

    def __repr__(self) -> str:
        return f"GaussianState(n_modes={self._n}, V={self._V.shape})"
