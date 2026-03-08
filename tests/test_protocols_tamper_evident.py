"""Tests for protocols.tamper_evident: run_legitimate_teleport, run_thief_teleport."""
from __future__ import annotations

import numpy as np
import pytest

from src.core_compute.state import State, ket0
from src.core_compute.protocols.tamper_evident import run_legitimate_teleport, run_thief_teleport


def test_legitimate_teleport_fidelity_one():
    msg = ket0()
    f = run_legitimate_teleport(msg)
    assert f == pytest.approx(1.0)


def test_thief_teleport_returns_fidelity_in_range():
    msg = State(np.array([1, 1], dtype=np.complex128).reshape(-1, 1) / np.sqrt(2), 1)
    f_legit = run_legitimate_teleport(msg)
    assert f_legit == pytest.approx(1.0)
    f_thief = run_thief_teleport(msg, thief_angle=0.3)
    assert 0.0 <= f_thief <= 1.0 + 1e-10
    # With nonzero thief angle, Bob's reduced state is disturbed; fidelity should be <= 1
    # (may be 1.0 for some messages/angles due to symmetry; we only check it's in range)
