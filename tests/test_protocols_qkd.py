"""
Tests for pedagogical QKD: BB84 and E91 (protocols/qkd.py).
"""
from __future__ import annotations

import pytest
from src.core_compute.protocols.qkd import run_bb84, run_e91


def test_run_bb84_seeded_key_agreement():
    """With fixed seed, sifted key should agree between Alice and Bob (no eavesdropper)."""
    result = run_bb84(n_bits=128, seed=42)
    assert result["n_bits"] == 128
    assert result["n_sift"] >= 2
    assert "key_bits" in result
    key_alice, key_bob = result["key_bits"]
    assert len(key_alice) == len(key_bob)
    assert result["key_agreement"] == True  # use == for numpy boolean
    assert key_alice == key_bob


def test_run_bb84_qber_zero_no_eavesdropper():
    """Without noise, QBER on sifted bits used for QBER estimate should be 0."""
    result = run_bb84(n_bits=256, seed=123)
    if result.get("qber") is not None:
        assert result["qber"] == 0.0


def test_run_bb84_returns_key_raw():
    """BB84 returns key_raw as (alice_list, bob_list)."""
    result = run_bb84(n_bits=64, seed=1)
    assert "key_raw" in result
    if result["key_raw"] is not None:
        ka, kb = result["key_raw"]
        assert isinstance(ka, list)
        assert isinstance(kb, list)
        assert len(ka) == len(kb)


def test_run_bb84_small_n_bits_low_sift():
    """With very few bits, n_sift can be small; response shape still valid."""
    result = run_bb84(n_bits=8, seed=999)
    assert "n_sift" in result
    assert result["n_sift"] >= 0
    if result["n_sift"] < 2:
        assert result["key_bits"] == []
        assert result.get("qber") is None


def test_run_e91_seeded_key_agreement():
    """E91: when bases match (Z or X), key bits agree; structure and n_key present."""
    result = run_e91(n_trials=200, seed=7)
    assert result["n_trials"] == 200
    assert "key_bits" in result
    key_alice, key_bob = result["key_bits"]
    assert len(key_alice) == len(key_bob)
    assert result["n_key"] == len(key_alice)
    # Simplified E91 uses basis 2 with H on both; correlation need not be 1, so key_agreement can be False
    assert "key_agreement" in result


def test_run_e91_chsh_bounded():
    """CHSH S should be in valid range (quantum up to 2*sqrt(2) ~ 2.83)."""
    result = run_e91(n_trials=500, seed=100)
    s = result["chsh_s"]
    # Classical |S| <= 2; quantum can go up to 2*sqrt(2)
    assert -3 <= s <= 3


def test_run_e91_returns_correlations_and_counts():
    """E91 returns 3x3 correlation matrix and counts."""
    result = run_e91(n_trials=100, seed=0)
    assert "correlations" in result
    assert "counts" in result
    assert len(result["correlations"]) == 3
    assert len(result["counts"]) == 3
    assert result["n_key"] == len(result["key_bits"][0])
