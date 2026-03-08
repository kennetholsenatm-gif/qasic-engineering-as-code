"""Tests for toy CV quantum radar: cv_state, cv_gates, quantum_radar."""
from __future__ import annotations

import numpy as np
import pytest

from src.core_compute.state.cv_state import GaussianState, vacuum_covariance, thermal_covariance, symplectic_form
from src.core_compute.state.cv_gates import two_mode_squeezing, beam_splitter, tmsv_covariance
from src.core_compute.protocols.quantum_radar import (
    tmsv_through_loss,
    state_H0_target_absent,
    mutual_information,
    run_quantum_radar,
)


def test_vacuum_covariance():
    V = vacuum_covariance(2)
    assert V.shape == (4, 4)
    np.testing.assert_allclose(V, np.eye(4) / 2.0)


def test_tmsv_symplectic_eigenvalues():
    # Pure TMSV: both symplectic eigenvalues 1/2
    V = tmsv_covariance(0.5)
    s = GaussianState(V, n_modes=2, check_physical=False)
    nu = s.symplectic_eigenvalues()
    assert nu.shape == (2,)
    np.testing.assert_allclose(nu, [0.5, 0.5], atol=1e-8)


def test_beam_splitter_symplectic():
    Om = symplectic_form(2)
    S = beam_splitter(0.3)
    np.testing.assert_allclose(S @ Om @ S.T, Om, atol=1e-10)


def test_tmsv_through_loss_shape():
    state = tmsv_through_loss(eta=0.1, n_b=1.0, r=0.3)
    assert state.n_modes == 2
    assert state.V.shape == (4, 4)


def test_mutual_info_H0_zero():
    state_H0 = state_H0_target_absent(r=0.5, n_b=10.0)
    I = mutual_information(state_H0)
    assert I == pytest.approx(0.0, abs=1e-10)


def test_mutual_info_H1_positive():
    state_H1 = tmsv_through_loss(eta=0.2, n_b=1.0, r=0.6)
    I = mutual_information(state_H1)
    assert I >= 0.0
    assert I > 0.001  # some correlation when eta > 0


def test_run_quantum_radar():
    out = run_quantum_radar(eta=0.1, n_b=5.0, r=0.4)
    assert out["mutual_info_H0"] == pytest.approx(0.0, abs=1e-8)
    assert out["mutual_info_H1"] > 0
    assert out["return_variance_H1"] < out["return_variance_H0"]
