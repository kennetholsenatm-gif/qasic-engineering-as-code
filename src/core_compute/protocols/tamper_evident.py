"""
Tamper-evidence: when a "Thief" intercepts or disturbs the quantum channel,
the receiver (Bob) sees a drop in fidelity. No cloning + monogamy → detectable.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core_compute.state import State
from src.core_compute.protocols.teleportation import teleport_circuit, _full_state_to_density, _partial_trace_qubits, _density_to_pure_state


def _rx(theta: float) -> np.ndarray:
    """Rotation around X: e^{-i X θ/2}."""
    c, s = np.cos(theta / 2), -1j * np.sin(theta / 2)
    return np.array([[c, s], [s, c]], dtype=np.complex128)


def run_legitimate_teleport(msg_state: State) -> float:
    """Run teleportation with no interference. Returns fidelity of Bob's state to original message."""
    from src.core_compute.protocols.teleportation import teleport
    received = teleport(msg_state)
    return msg_state.fidelity(received)


def run_thief_teleport(
    msg_state: State,
    thief_angle: float = 0.3,
    thief_qubit: int = 2,
) -> float:
    """
    Thief disturbs Bob's qubit (qubit 2) by applying Rx(thief_angle) before we "read out".
    Returns fidelity of Bob's state to original message (should be < 1).
    """
    full = teleport_circuit(msg_state)
    full = full.apply(_rx(thief_angle), [thief_qubit])
    rho = _full_state_to_density(full)
    rho_2 = _partial_trace_qubits(rho, [0, 1], 3)
    received = _density_to_pure_state(rho_2)
    return msg_state.fidelity(received)


def fidelity_after_thief(
    msg_state: State,
    thief_angle: float,
) -> float:
    """Fidelity of received state (after Thief's Rx on Bob's qubit) to original |ψ⟩."""
    return run_thief_teleport(msg_state, thief_angle=thief_angle)


if __name__ == "__main__":
    from state import ket0, ket1
    alpha = np.sqrt(0.7)
    beta = np.sqrt(0.3)
    msg = State(np.array([alpha, beta], dtype=np.complex128).reshape(-1, 1), 1)
    f_legit = run_legitimate_teleport(msg)
    f_thief = run_thief_teleport(msg, thief_angle=0.5)
    print(f"Legitimate teleport fidelity: {f_legit:.6f} (expect 1.0)")
    print(f"With Thief (Rx(0.5) on Bob qubit) fidelity: {f_thief:.6f} (expect < 1)")
