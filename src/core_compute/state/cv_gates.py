"""
Symplectic matrices for continuous-variable Gaussian operations.

All operations preserve the symplectic form: S Omega S^T = Omega.
Applied to covariance as V' = S V S^T. Quadrature order (q1, p1, q2, p2, ...).
"""
from __future__ import annotations

import numpy as np


def two_mode_squeezing(r: float) -> np.ndarray:
    """
    Symplectic matrix for two-mode squeezing with parameter r (squeezing strength).
    Acts on two modes (4x4). Applied to vacuum yields TMSV with covariance
    V = (1/2) [[ cosh(2r) I2, sinh(2r) Z ], [ sinh(2r) Z, cosh(2r) I2 ]], Z = diag(1,-1).
    """
    cr = np.cosh(r)
    sr = np.sinh(r)
    I2 = np.eye(2, dtype=np.float64)
    Z = np.diag([1.0, -1.0])
    return np.block([[cr * I2, sr * Z], [sr * Z, cr * I2]])


def beam_splitter(transmittance: float) -> np.ndarray:
    """
    Beam splitter symplectic (4x4) mixing two modes.
    transmittance T: output port 1 gets sqrt(T) of input 1 and sqrt(1-T) of input 2.
    Reflectance R = 1 - T. S = [[ sqrt(T)I2, sqrt(R)I2 ], [ -sqrt(R)I2, sqrt(T)I2 ]].
    """
    if not 0 <= transmittance <= 1:
        raise ValueError("transmittance must be in [0, 1]")
    t = np.sqrt(transmittance)
    r = np.sqrt(1.0 - transmittance)
    I2 = np.eye(2, dtype=np.float64)
    return np.block([[t * I2, r * I2], [-r * I2, t * I2]])


def tmsv_covariance(r: float) -> np.ndarray:
    """
    Covariance matrix of two-mode squeezed vacuum (TMSV) with squeezing r.
    V = (1/2) S S^T where S = two_mode_squeezing(r); standard form with a = b = cosh(2r)/2,
    c+ = sinh(2r)/2, c- = -sinh(2r)/2.
    """
    c2 = np.cosh(2.0 * r)
    s2 = np.sinh(2.0 * r)
    I2 = np.eye(2, dtype=np.float64)
    Z = np.diag([1.0, -1.0])
    return 0.5 * np.block([[c2 * I2, s2 * Z], [s2 * Z, c2 * I2]])
