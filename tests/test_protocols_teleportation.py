"""Tests for protocols.teleportation: teleport_circuit, teleport."""
from __future__ import annotations

import numpy as np
import pytest

from src.core_compute.state import State, product_state, ket0, ket1
from src.core_compute.protocols.teleportation import teleport_circuit, teleport


def test_teleport_returns_same_state():
    msg = ket0()
    received = teleport(msg)
    assert msg.fidelity(received) == pytest.approx(1.0)
    msg1 = ket1()
    received1 = teleport(msg1)
    assert msg1.fidelity(received1) == pytest.approx(1.0)


def test_teleport_circuit_three_qubits():
    msg = State(np.array([1, 1], dtype=np.complex128).reshape(-1, 1) / np.sqrt(2), 1)
    full = teleport_circuit(msg)
    assert full.n_qubits == 3


def test_teleport_circuit_rejects_multi_qubit_msg():
    msg = product_state("0", "0")
    with pytest.raises(ValueError, match="msg_state must be 1 qubit"):
        teleport_circuit(msg)
