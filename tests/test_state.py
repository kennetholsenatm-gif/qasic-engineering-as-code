"""Tests for state.State, product_state, bell_pair, fidelity."""
from __future__ import annotations

import numpy as np
import pytest

from state import State, product_state, bell_pair, ket0, ket1


def test_ket0_ket1():
    z = ket0()
    o = ket1()
    assert z.n_qubits == 1 and o.n_qubits == 1
    np.testing.assert_allclose(z.vec.ravel(), [1, 0])
    np.testing.assert_allclose(o.vec.ravel(), [0, 1])
    assert z.fidelity(z) == pytest.approx(1.0)
    assert z.fidelity(o) == pytest.approx(0.0)


def test_product_state_requires_at_least_one_ket():
    with pytest.raises(ValueError, match="at least one ket"):
        product_state()


def test_product_state_strings():
    s = product_state("0", "1")
    assert s.n_qubits == 2
    # kron(|0>, |1>) = [0,1,0,0] (amplitude 1 at index 1)
    np.testing.assert_allclose(s.vec.ravel(), [0, 1, 0, 0])


def test_product_state_normalized():
    s = product_state("0", "0", "0")
    assert s.n_qubits == 3
    assert np.abs(np.linalg.norm(s.vec) - 1.0) < 1e-10


def test_bell_pair_phi_plus():
    b = bell_pair("Phi+")
    assert b.n_qubits == 2
    assert np.abs(np.linalg.norm(b.vec) - 1.0) < 1e-10
    # Phi+ is maximally entangled: two nonzero amplitudes, not a product state
    nz = np.count_nonzero(np.abs(b.vec.ravel()) > 1e-10)
    assert nz == 2


def test_bell_pair_unknown_raises():
    with pytest.raises(ValueError, match="Unknown Bell state"):
        bell_pair("invalid")


def test_fidelity_same_state():
    b = bell_pair("Phi+")
    assert b.fidelity(b) == pytest.approx(1.0)


def test_fidelity_mismatched_qubits_raises():
    a = ket0()
    b = product_state("0", "0")
    with pytest.raises(ValueError, match="Mismatched qubit count"):
        a.fidelity(b)


def test_state_copy():
    b = bell_pair("Phi+")
    c = b.copy()
    assert c.n_qubits == b.n_qubits
    np.testing.assert_allclose(c.vec, b.vec)
    c._vec[0, 0] = 0
    assert b.fidelity(c) < 1.0  # b unchanged
