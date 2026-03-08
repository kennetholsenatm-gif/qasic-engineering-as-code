"""Tests for engineering.metasurface_inverse_net: create_model, example_forward_pass, _topology_from_routing."""
from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path

import pytest

import torch

from src.core_compute.engineering.metasurface_inverse_net import (
    create_model,
    example_forward_pass,
    parse_phase_band,
    _topology_from_routing,
    MetasurfaceInverseNet,
)


def test_create_model():
    model = create_model(target_topology_features=10, num_meta_atoms=100, device="cpu")
    assert isinstance(model, MetasurfaceInverseNet)
    assert model.target_params_size == 10
    assert model.num_meta_atoms == 100


def test_example_forward_pass_shape_and_range():
    phase = example_forward_pass(
        target_topology_features=5,
        num_meta_atoms=20,
        batch_size=2,
        device="cpu",
        seed=42,
    )
    assert phase.shape == (2, 20)
    assert phase.min() >= 0 and phase.max() <= 2 * math.pi + 1e-5
    assert phase.dtype in (torch.float32, torch.float64)


def test_parse_phase_band():
    assert parse_phase_band(None) is None
    assert parse_phase_band("") is None
    assert parse_phase_band("full") is None
    lo, hi = parse_phase_band("pi")
    assert abs(lo - (math.pi - 0.14)) < 1e-9
    assert abs(hi - (math.pi + 0.14)) < 1e-9
    lo, hi = parse_phase_band("3.033,3.284")
    assert abs(lo - 3.033) < 1e-9 and abs(hi - 3.284) < 1e-9


def test_phase_band_constrains_output():
    phase_band = (3.033, 3.284)
    phase = example_forward_pass(
        target_topology_features=5,
        num_meta_atoms=50,
        batch_size=2,
        device="cpu",
        seed=123,
        phase_band=phase_band,
    )
    assert phase.shape == (2, 50)
    assert phase.min() >= 3.033 - 1e-5 and phase.max() <= 3.284 + 1e-5


def test_create_model_with_phase_band():
    phase_band = (math.pi - 0.14, math.pi + 0.14)
    model = create_model(
        target_topology_features=4,
        num_meta_atoms=8,
        device="cpu",
        phase_band=phase_band,
    )
    assert model.phase_lo == phase_band[0] and model.phase_hi == phase_band[1]
    x = torch.randn(1, 4)
    out = model(x)
    assert out.shape == (1, 8)
    assert out.min() >= phase_band[0] - 1e-5 and out.max() <= phase_band[1] + 1e-5


def test_topology_from_routing_minimal_json():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({
            "mapping": [{"logical": 0, "physical": 0}, {"logical": 1, "physical": 1}],
            "backend": "ibm_torino",
        }, f)
        path = f.name
    try:
        vec = _topology_from_routing(path, target_dim=10, device=torch.device("cpu"))
        assert vec.shape == (1, 10)
        assert vec.dtype == torch.float32
    finally:
        Path(path).unlink(missing_ok=True)


def test_topology_from_routing_empty_mapping():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"mapping": [], "backend": ""}, f)
        path = f.name
    try:
        vec = _topology_from_routing(path, target_dim=10, device=torch.device("cpu"))
        assert vec.shape == (1, 10)
    finally:
        Path(path).unlink(missing_ok=True)


def test_topology_from_routing_missing_file_raises():
    with pytest.raises(FileNotFoundError, match="not found"):
        _topology_from_routing("/nonexistent/routing.json", 10, torch.device("cpu"))


def test_parse_phase_band_invalid_raises():
    with pytest.raises(ValueError, match="phase_band"):
        parse_phase_band("1,2,3")


def test_topology_from_routing_invalid_json_raises():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("{ invalid json")
        path = f.name
    try:
        with pytest.raises(ValueError, match="Invalid JSON"):
            _topology_from_routing(path, 10, torch.device("cpu"))
    finally:
        Path(path).unlink(missing_ok=True)
