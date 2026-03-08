"""
Discrete Variable (DV) Toy Quantum Illumination.

Seth Lloyd's 2008 Quantum Illumination (discrete single photons) as a qubit toy:
- Prepare: Bell pair (Idler=qubit 0, Signal=qubit 1).
- H1 (target present): Signal hits target; with probability η returns unchanged,
  with probability 1-η lost and replaced by thermal background ρ = I/2.
- H0 (target absent): Signal completely lost; receiver gets thermal ρ = I/2.
- Measure: Joint Bell-basis measurement on (Idler, Return).

We compare error probability (and Chernoff exponent) of this entangled probe
vs sending a single unentangled |1⟩ photon.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core_compute.state.density import DensityState
from src.core_compute.state.channels import kraus_thermal_loss, thermal_loss

CDTYPE = np.complex128

# Bell basis projectors (2-qubit): |Φ+⟩⟨Φ+|, |Φ-⟩⟨Φ-|, |Ψ+⟩⟨Ψ+|, |Ψ-⟩⟨Ψ-|
# Basis order: |00⟩,|01⟩,|10⟩,|11⟩ (qubit 0 = LSB). Orthonormal and sum to I.
def _bell_projectors() -> list[np.ndarray]:
    o = 1.0 / np.sqrt(2)
    phi_plus = np.array([1, 0, 0, 1], dtype=CDTYPE) * o
    phi_minus = np.array([1, 0, 0, -1], dtype=CDTYPE) * o
    psi_plus = np.array([0, 1, 1, 0], dtype=CDTYPE) * o
    psi_minus = np.array([0, 1, -1, 0], dtype=CDTYPE) * o
    return [np.outer(v, v.conj()) for v in (phi_plus, phi_minus, psi_plus, psi_minus)]


def _bell_density_phi_plus() -> np.ndarray:
    """|Φ+⟩⟨Φ+| with |Φ+⟩ = (|00⟩+|11⟩)/√2 in basis order |00⟩,|01⟩,|10⟩,|11⟩ (qubit 0 = LSB)."""
    v = np.array([1, 0, 0, 1], dtype=CDTYPE) / np.sqrt(2)
    return np.outer(v, v.conj())


def rho_H1(eta: float) -> DensityState:
    """
    Two-qubit state under H1 (target present): Bell pair with thermal loss on Signal (qubit 1).
    E(ρ) = η ρ + (1-η) I/2 on the signal qubit.
    """
    rho = DensityState(_bell_density_phi_plus(), 2)
    return rho.apply_channel(1, kraus_thermal_loss(eta))


def rho_H0() -> DensityState:
    """
    Two-qubit state under H0 (target absent): Signal lost, only thermal background.
    (Idler, Return) = (I/2) ⊗ (I/2) = I_4/4.
    """
    rho = np.eye(4, dtype=CDTYPE) / 4
    return DensityState(rho, 2)


def bell_outcome_probabilities(rho: DensityState) -> np.ndarray:
    """Probability of each of the 4 Bell outcomes (Phi+, Phi-, Psi+, Psi-) for 2-qubit rho."""
    projectors = _bell_projectors()
    probs = np.array([float(np.real(np.trace(P @ rho.rho))) for P in projectors])
    return probs


def minimum_error_probability(p0: np.ndarray, p1: np.ndarray, prior0: float = 0.5) -> float:
    """
    Minimum error probability for binary hypothesis with outcome distributions p0, p1.
    Equal priors: P_err = (1/2) sum_k min(p0(k), p1(k)).
    """
    prior1 = 1 - prior0
    return float(np.sum(np.minimum(prior0 * p0, prior1 * p1)))


def chernoff_exponent(p0: np.ndarray, p1: np.ndarray) -> float:
    """
    Chernoff exponent (single-shot): C = max_{0≤s≤1} -log sum_k p0(k)^s p1(k)^{1-s}.
    For n copies, P_err ≤ (1/2) exp(-n C) (asymptotically).
    """
    s_vals = np.linspace(1e-6, 1 - 1e-6, 50)
    p0 = np.maximum(p0, 1e-20)
    p1 = np.maximum(p1, 1e-20)
    rates = [-np.log(np.sum(p0**s * p1**(1 - s))) for s in s_vals]
    return float(max(rates))


def entangled_probe_metrics(eta: float) -> dict:
    """
    Error probability and Chernoff exponent for the entangled (Bell-pair) probe.
    Returns dict with p_H0, p_H1 (4-vec), P_err, chernoff_exponent.
    """
    r1 = rho_H1(eta)
    r0 = rho_H0()
    p_H1 = bell_outcome_probabilities(r1)
    p_H0 = bell_outcome_probabilities(r0)
    P_err = minimum_error_probability(p_H0, p_H1)
    C = chernoff_exponent(p_H0, p_H1)
    return {"p_H0": p_H0, "p_H1": p_H1, "P_err": P_err, "chernoff_exponent": C}


def unentangled_probe_metrics(eta: float) -> dict:
    """
    Single unentangled |1⟩ probe: H1 applies thermal_loss(eta) to |1⟩⟨1|, H0 gives I/2.
    Computational-basis measurement: P(0|H0)=1/2, P(1|H0)=1/2;
    P(0|H1)=(1-η)/2, P(1|H1)=η+(1-η)/2=(1+η)/2.
    """
    ket1 = np.array([[0], [1]], dtype=CDTYPE)
    rho_signal_H1_1q = thermal_loss(np.outer(ket1.ravel(), ket1.ravel().conj()), 0, eta, 1)
    p_H0 = np.array([0.5, 0.5])
    p_H1 = np.array([float(np.real(rho_signal_H1_1q[0, 0])), float(np.real(rho_signal_H1_1q[1, 1]))])
    P_err = minimum_error_probability(p_H0, p_H1)
    C = chernoff_exponent(p_H0, p_H1)
    return {"p_H0": p_H0, "p_H1": p_H1, "P_err": P_err, "chernoff_exponent": C}


def run_comparison(eta: float = 0.1) -> None:
    """Print entangled vs unentangled error probability and Chernoff exponent."""
    ent = entangled_probe_metrics(eta)
    unent = unentangled_probe_metrics(eta)
    print("DV Quantum Illumination (toy)")
    print("  Reflectivity eta =", eta)
    print("  Entangled (Bell) probe:  P_err = {:.6f}, Chernoff exponent = {:.6f}".format(
        ent["P_err"], ent["chernoff_exponent"]))
    print("  Unentangled (|1>) probe: P_err = {:.6f}, Chernoff exponent = {:.6f}".format(
        unent["P_err"], unent["chernoff_exponent"]))
    print("  Advantage: entangled P_err lower by {:.6f}; Chernoff higher by {:.6f}".format(
        unent["P_err"] - ent["P_err"], ent["chernoff_exponent"] - unent["chernoff_exponent"]))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="DV Quantum Illumination toy: entangled vs unentangled probe")
    parser.add_argument("--eta", type=float, default=0.1, help="Reflectivity (survival probability)")
    args = parser.parse_args()
    run_comparison(args.eta)
