"""Tests for DV Quantum Illumination protocol and thermal loss channel."""
from __future__ import annotations

import numpy as np
import pytest

from src.core_compute.state.density import DensityState, fidelity_pure_vs_density
from src.core_compute.state.channels import kraus_thermal_loss, thermal_loss
from src.core_compute.protocols.quantum_illumination import (
    rho_H0,
    rho_H1,
    bell_outcome_probabilities,
    minimum_error_probability,
    entangled_probe_metrics,
    unentangled_probe_metrics,
)


def test_thermal_loss_channel_eta_one():
    """thermal_loss(eta=1) is identity."""
    rho = np.outer(np.array([0, 1], dtype=complex), np.array([0, 1], dtype=complex).conj())
    out = thermal_loss(rho, 0, 1.0, 1)
    np.testing.assert_allclose(out, rho, atol=1e-10)


def test_thermal_loss_channel_eta_zero():
    """thermal_loss(eta=0) replaces with I/2."""
    rho = np.outer(np.array([0, 1], dtype=complex), np.array([0, 1], dtype=complex).conj())
    out = thermal_loss(rho, 0, 0.0, 1)
    np.testing.assert_allclose(out, np.eye(2, dtype=complex) / 2, atol=1e-10)


def test_rho_H0_is_maximally_mixed():
    """H0: (Idler, Return) = I/4."""
    r0 = rho_H0()
    assert r0.n_qubits == 2
    np.testing.assert_allclose(r0.rho, np.eye(4, dtype=complex) / 4, atol=1e-10)


def test_rho_H1_eta_one_is_bell():
    """H1 with eta=1: signal unchanged, state is |Φ+⟩⟨Φ+|."""
    r1 = rho_H1(1.0)
    # |Φ+⟩ = (|00⟩+|11⟩)/√2 in LSB order
    from src.core_compute.state import State
    v = np.array([1, 0, 0, 1], dtype=complex) / np.sqrt(2)
    phi_plus = State(v.reshape(-1, 1), 2)
    assert fidelity_pure_vs_density(phi_plus, r1.rho) == pytest.approx(1.0, abs=1e-8)


def test_rho_H1_eta_zero():
    """H1 with eta=0: signal qubit replaced by I/2; trace 1 and reduced state of qubit 1 is I/2."""
    r1 = rho_H1(0.0)
    assert r1.n_qubits == 2
    assert np.real(np.trace(r1.rho)) == pytest.approx(1.0)
    # Partial trace over qubit 0 (idler): reduce to qubit 1. Reshape (4,4) -> (q1,q0,q1',q0') so row = q0+2*q1.
    r4 = r1.rho.reshape(2, 2, 2, 2)  # r4[q1,q0,q1',q0'] = rho[q0+2*q1, q0'+2*q1']
    rho1 = np.einsum("acbc->ab", r4)  # trace over qubit 0: rho1[q1,q1'] = sum_q0 r4[q1,q0,q1',q0]
    np.testing.assert_allclose(rho1, np.eye(2, dtype=complex) / 2, atol=1e-8)


def test_bell_outcome_probabilities_sum_to_one():
    r0 = rho_H0()
    r1 = rho_H1(0.2)
    assert np.sum(bell_outcome_probabilities(r0)) == pytest.approx(1.0)
    assert np.sum(bell_outcome_probabilities(r1)) == pytest.approx(1.0)


def test_entangled_beats_unentangled():
    """Entangled probe has lower P_err than unentangled for eta in (0,1)."""
    ent = entangled_probe_metrics(0.1)
    unent = unentangled_probe_metrics(0.1)
    assert ent["P_err"] < unent["P_err"]
    assert ent["chernoff_exponent"] > unent["chernoff_exponent"]


def test_minimum_error_probability_equal_priors():
    p0 = np.array([0.5, 0.5])
    p1 = np.array([0.5, 0.5])
    assert minimum_error_probability(p0, p1) == pytest.approx(0.5)
