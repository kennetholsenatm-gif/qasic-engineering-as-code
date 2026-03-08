"""Tests for optional engineering demos: scqubits, QuTiP, forward_prediction_net, SuperScreen."""
from __future__ import annotations

import pytest

from src.core_compute.engineering.forward_prediction_net import (
    ForwardPredictionNet,
    create_model,
    synthetic_training_stub,
)


def test_forward_prediction_net_create_and_forward():
    model = create_model(config_size=10, output_size=2, device="cpu")
    assert isinstance(model, ForwardPredictionNet)
    assert model.config_size == 10 and model.output_size == 2
    import torch
    x = torch.randn(3, 10)
    y = model(x)
    assert y.shape == (3, 2)


def test_forward_prediction_net_synthetic_training_stub():
    loss = synthetic_training_stub(
        config_size=8,
        output_size=2,
        steps=5,
        device="cpu",
        seed=42,
    )
    assert isinstance(loss, float)
    assert loss >= 0


def test_squid_spectrum_scqubits():
    pytest.importorskip("scqubits")
    pytest.importorskip("numpy")
    from src.core_compute.engineering.squid_spectrum_scqubits import _fluxonium_spectrum_and_sweet_spots
    import numpy as np
    flux_vals = np.linspace(-0.3, 0.3, 11)
    flux, evals, sweet = _fluxonium_spectrum_and_sweet_spots(flux_vals, evals_count=3)
    assert flux.shape == (11,)
    assert evals.shape == (11, 3)
    assert isinstance(sweet, list)


def test_open_system_qutip():
    pytest.importorskip("qutip")
    pytest.importorskip("numpy")
    from src.core_compute.engineering.open_system_qutip import run_lindblad_demo
    result = run_lindblad_demo(gamma1=0.1, gamma2=0.05, tmax=1.0, n_points=21)
    assert "expect_sigmaz" in result
    assert len(result["expect_sigmaz"]) == 21
    assert result["gamma1"] == 0.1


def test_superscreen_demo():
    pytest.importorskip("superscreen")
    from src.core_compute.engineering.superscreen_demo import run_minimal_demo
    ok = run_minimal_demo(save_plot=None)
    assert ok is True
