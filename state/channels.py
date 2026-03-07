"""
Noise channels for quantum links: Kraus operators and application to density matrices.
Supports depolarizing, amplitude damping, phase damping, optional thermal and detector loss.
Used to simulate atmospheric attenuation, thermal fluctuations, and imperfect detectors
(weather-resilient SATCOM, environmental degradation).
"""
from __future__ import annotations

import numpy as np
from typing import Sequence

CDTYPE = np.complex128


# --- Single-qubit Pauli matrices (for Kraus operators) ---
_I = np.array([[1, 0], [0, 1]], dtype=CDTYPE)
_X = np.array([[0, 1], [1, 0]], dtype=CDTYPE)
_Y = np.array([[0, -1j], [1j, 0]], dtype=CDTYPE)
_Z = np.array([[1, 0], [0, -1]], dtype=CDTYPE)


def kraus_depolarizing(p: float) -> list[np.ndarray]:
    """
    Depolarizing channel: with probability p, apply X, Y, or Z uniformly (each p/4);
    with probability 1-p leave identity. Standard model for generic qubit errors.
    Kraus: K0 = sqrt(1 - 3p/4) I, K1 = sqrt(p/4) X, K2 = sqrt(p/4) Y, K3 = sqrt(p/4) Z.
    """
    if not 0 <= p <= 1:
        raise ValueError("depolarizing p must be in [0, 1]")
    c = np.sqrt(1 - 3 * p / 4)
    s = np.sqrt(p / 4)
    return [c * _I, s * _X, s * _Y, s * _Z]


def kraus_amplitude_damping(gamma: float) -> list[np.ndarray]:
    """
    Amplitude damping (T1-like): |1⟩ → |0⟩ with probability gamma.
    K0 = [[1, 0], [0, sqrt(1-gamma)]], K1 = [[0, sqrt(gamma)], [0, 0]].
    Parameter: gamma in [0, 1]. T1 can be mapped via gamma = 1 - exp(-t/T1).
    """
    if not 0 <= gamma <= 1:
        raise ValueError("amplitude_damping gamma must be in [0, 1]")
    g = np.sqrt(gamma)
    s = np.sqrt(1 - gamma)
    K0 = np.array([[1, 0], [0, s]], dtype=CDTYPE)
    K1 = np.array([[0, g], [0, 0]], dtype=CDTYPE)
    return [K0, K1]


def kraus_phase_damping(lambda_p: float) -> list[np.ndarray]:
    """
    Phase damping / dephasing (T2-like): decays off-diagonal coherence.
    K0 = diag(1, sqrt(1-lambda)), K1 = diag(0, sqrt(lambda)).
    Parameter: lambda_p in [0, 1].
    """
    if not 0 <= lambda_p <= 1:
        raise ValueError("phase_damping lambda must be in [0, 1]")
    s = np.sqrt(1 - lambda_p)
    g = np.sqrt(lambda_p)
    K0 = np.array([[1, 0], [0, s]], dtype=CDTYPE)
    K1 = np.array([[0, 0], [0, g]], dtype=CDTYPE)
    return [K0, K1]


def kraus_thermal(p_ex: float) -> list[np.ndarray]:
    """
    Simple thermal channel (full replacement): E(rho) = (1 - p_ex)|0⟩⟨0| + p_ex|1⟩⟨1|.
    p_ex = excitation probability (effective temperature). Uses the constant-output
    Kraus construction so that any input state is replaced by the thermal state.
    """
    if not 0 <= p_ex <= 1:
        raise ValueError("thermal p_ex must be in [0, 1]")
    # Kraus for E(rho) = sigma with sigma = (1-p_ex)|0><0| + p_ex|1><1|:
    # K0 = [[sqrt(1-p_ex), 0], [sqrt(p_ex), 0]], K1 = [[0, sqrt(1-p_ex)], [0, sqrt(p_ex)]] (sum K_i^dag K_i = I).
    p0 = 1 - p_ex
    s0 = np.sqrt(p0)
    s1 = np.sqrt(p_ex)
    K0 = np.array([[s0, 0], [s1, 0]], dtype=CDTYPE)
    K1 = np.array([[0, s0], [0, s1]], dtype=CDTYPE)
    return [K0, K1]


def kraus_detector_loss(eta: float) -> list[np.ndarray]:
    """
    Detector inefficiency / loss: with probability (1 - eta) the qubit is "lost"
    and replaced by |0⟩⟨0| (or we could use mixed). eta = efficiency in [0, 1].
    Model: with prob eta ideal, with prob 1-eta replace by |0><0|.
    Kraus: K0 = sqrt(eta) I, K1 = sqrt(1-eta) |0><0| (projects to 0), K2 = sqrt(1-eta) |0><1| (annihilates 1).
    Actually loss channel: K0 = [[1,0],[0,sqrt(eta)]], K1 = [[0, sqrt(1-eta)], [0, 0]]. Same as amplitude damping with gamma = 1-eta.
    """
    if not 0 <= eta <= 1:
        raise ValueError("detector_loss eta must be in [0, 1]")
    return kraus_amplitude_damping(1 - eta)


def kraus_thermal_loss(eta: float) -> list[np.ndarray]:
    """
    Thermal loss channel (radar / target reflection): E(ρ) = η ρ + (1-η) I/2.
    With probability η the state is unchanged; with probability 1-η it is replaced by
    the maximally mixed state I/2 (thermal background). Used in DV Quantum Illumination.
    Parameter eta in [0, 1] (reflectivity / survival probability).
    Kraus: K0 = sqrt(η) I, K1..4 = sqrt((1-η)/4) I, X, Y, Z (so (1-η)/4 (ρ+XρX+YρY+ZρZ) = (1-η) I/2).
    """
    if not 0 <= eta <= 1:
        raise ValueError("thermal_loss eta must be in [0, 1]")
    a = np.sqrt(eta)
    b = np.sqrt((1 - eta) / 4)
    return [a * _I, b * _I, b * _X, b * _Y, b * _Z]


def apply_single_qubit_channel(
    rho: np.ndarray,
    qubit: int,
    kraus_ops: Sequence[np.ndarray],
    n_qubits: int | None = None,
) -> np.ndarray:
    """
    Apply a single-qubit channel (Kraus operators) to the given qubit of an n-qubit
    density matrix rho (shape 2^n x 2^n). Implements ρ → Σ_i K_i ρ K_i†.
    Qubit index 0 is LSB. Returns the evolved density matrix.
    """
    rho = np.asarray(rho, dtype=CDTYPE)
    if rho.ndim != 2 or rho.shape[0] != rho.shape[1]:
        raise ValueError("rho must be a square matrix")
    n = n_qubits if n_qubits is not None else max(0, int(np.round(np.log2(rho.shape[0]))))
    if rho.shape[0] != 2**n:
        raise ValueError("rho size must be 2^n")
    if not 0 <= qubit < n:
        raise ValueError("qubit index out of range")

    # Permute so that the target qubit is the last (LSB) in the row/col index.
    # Index i = i_rest * 2 + (i >> qubit) & 1, where i_rest is the (n-1)-bit index with qubit removed.
    def permute_index(i: int) -> int:
        low = i & ((1 << qubit) - 1)
        bit_q = (i >> qubit) & 1
        high = (i >> (qubit + 1)) << qubit
        return (high + low) << 1 | bit_q

    dim = 2**n
    perm = np.array([permute_index(i) for i in range(dim)])
    rho_p = rho[np.ix_(perm, perm)]

    # Reshape to (2^(n-1), 2, 2^(n-1), 2)
    dim_rest = 2 ** (n - 1)
    rho_2 = rho_p.reshape(dim_rest, 2, dim_rest, 2)

    # Apply channel: out_block = sum_i K_i @ block @ K_i^dag for each block
    out_2 = np.zeros_like(rho_2)
    for K in kraus_ops:
        K = np.asarray(K, dtype=CDTYPE)
        if K.shape != (2, 2):
            raise ValueError("Kraus op must be 2x2")
        # (dim_rest, 2, dim_rest, 2) @ K^dag on the (2,2) part: (..., 2, 2) @ (2,2) -> (..., 2, 2)
        # rho_2 has indices (a, i, b, j). We do sum_K K_ik rho_akbl K*_jl -> out_ailbj
        for i in range(2):
            for j in range(2):
                for k in range(2):
                    for l in range(2):
                        out_2[:, i, :, j] += K[i, k] * rho_2[:, k, :, l] * np.conj(K[j, l])

    out_p = out_2.reshape(dim, dim)
    # Inverse permutation
    inv_perm = np.argsort(perm)
    return out_p[np.ix_(inv_perm, inv_perm)]


def depolarizing(rho: np.ndarray, qubit: int, p: float, n_qubits: int | None = None) -> np.ndarray:
    """Apply depolarizing channel with probability p to the given qubit."""
    return apply_single_qubit_channel(rho, qubit, kraus_depolarizing(p), n_qubits)


def amplitude_damping(rho: np.ndarray, qubit: int, gamma: float, n_qubits: int | None = None) -> np.ndarray:
    """Apply amplitude damping (T1-like) with strength gamma to the given qubit."""
    return apply_single_qubit_channel(rho, qubit, kraus_amplitude_damping(gamma), n_qubits)


def phase_damping(rho: np.ndarray, qubit: int, lambda_p: float, n_qubits: int | None = None) -> np.ndarray:
    """Apply phase damping (T2-like) with parameter lambda to the given qubit."""
    return apply_single_qubit_channel(rho, qubit, kraus_phase_damping(lambda_p), n_qubits)


def thermal(rho: np.ndarray, qubit: int, p_ex: float, n_qubits: int | None = None) -> np.ndarray:
    """Apply thermal channel (replace with thermal state) with excitation probability p_ex."""
    return apply_single_qubit_channel(rho, qubit, kraus_thermal(p_ex), n_qubits)


def detector_loss(rho: np.ndarray, qubit: int, eta: float, n_qubits: int | None = None) -> np.ndarray:
    """Apply detector loss / inefficiency (eta = efficiency) to the given qubit."""
    return apply_single_qubit_channel(rho, qubit, kraus_detector_loss(eta), n_qubits)


def thermal_loss(rho: np.ndarray, qubit: int, eta: float, n_qubits: int | None = None) -> np.ndarray:
    """
    Apply thermal loss channel to the given qubit: E(ρ) = η ρ + (1-η) I/2.
    eta = reflectivity (survival probability); used in DV Quantum Illumination.
    """
    return apply_single_qubit_channel(rho, qubit, kraus_thermal_loss(eta), n_qubits)
