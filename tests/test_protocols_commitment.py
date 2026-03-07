"""Tests for protocols.commitment: run_commitment_protocol, verify_commitment, commit."""
from __future__ import annotations

import pytest

from protocols.commitment import (
    run_commitment_protocol,
    verify_commitment,
    commit,
    open_commitment,
)
from state import bell_pair


def test_verify_commitment_consistent():
    assert verify_commitment(0, 0, 0) is True
    assert verify_commitment(1, 1, 1) is True
    assert verify_commitment(0, 0, 1) is False


def test_run_commitment_protocol_returns_dict():
    out = run_commitment_protocol(0, seed=42)
    assert "committed_bit" in out
    assert "measurement_m" in out
    assert "bob_outcome" in out
    assert "verify_ok" in out
    assert out["verify_ok"] is True


def test_commit_bit_zero_or_one():
    bell = bell_pair("Phi+")
    b, m = commit(0, bell, rng=__import__("numpy").random.default_rng(42))
    assert b == 0
    assert m in (0, 1)
    b1, m1 = commit(1, bell, rng=__import__("numpy").random.default_rng(43))
    assert b1 == 1
    assert m1 in (0, 1)


def test_commit_invalid_bit_raises():
    bell = bell_pair("Phi+")
    with pytest.raises(ValueError, match="bit must be 0 or 1"):
        commit(2, bell)
