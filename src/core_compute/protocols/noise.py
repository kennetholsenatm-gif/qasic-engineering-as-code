"""
Noise model and noisy protocol execution.
Configurable injection of channels (depolarizing, amplitude damping, etc.) at named
circuit steps so demos can run teleport/tamper with environmental noise and compare
fidelity drop (environment vs tampering).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core_compute.state import State, product_state
from src.core_compute.state.gates import H, X, Z, CNOT
from src.core_compute.state.density import DensityState, state_to_density, fidelity_pure_vs_density
from src.core_compute.state import channels as ch

# Bob's correction gates (1-qubit)
_Z = np.array([[1, 0], [0, -1]], dtype=np.complex128)
_X = np.array([[0, 1], [1, 0]], dtype=np.complex128)

# Protocol qubit labels: 0=message, 1=alice, 2=bob. State index = msg*4+alice*2+bob so state qubit 0=bob, 1=alice, 2=msg
PROTOCOL_TO_STATE_QUBIT = {0: 2, 1: 1, 2: 0}

# Named injection points: map to step index after which to inject
INJECTION_AFTER_STEP = {
    "after_bell_creation": 2,
    "after_alice": 4,
    "before_readout": 4,
}


def _partial_trace_qubits(rho: np.ndarray, trace_out: list[int], n: int) -> np.ndarray:
    """Trace out qubits in trace_out. rho is 2^n x 2^n."""
    keep = [i for i in range(n) if i not in trace_out]
    dim_keep = 2 ** len(keep)
    rho_flat = rho.reshape([2] * (2 * n))
    for q in sorted(trace_out, reverse=True):
        rho_flat = np.trace(rho_flat, axis1=q, axis2=n + q)
    return rho_flat.reshape(dim_keep, dim_keep)


def _apply_channel_to_rho(
    rho: np.ndarray,
    n_qubits: int,
    channel_name: str,
    qubits: list[int],
    *,
    protocol_qubits: bool = True,
    **kwargs: Any,
) -> np.ndarray:
    """Apply a single-qubit channel by name to each qubit in qubits. Returns new rho.
    If protocol_qubits True, qubits are in protocol order (0=msg, 1=alice, 2=bob) and mapped to state index."""
    for q in qubits:
        q_state = PROTOCOL_TO_STATE_QUBIT.get(q, q) if protocol_qubits else q
        if channel_name == "depolarizing":
            p = kwargs.get("p", 0.05)
            rho = ch.apply_single_qubit_channel(rho, q_state, ch.kraus_depolarizing(p), n_qubits)
        elif channel_name == "amplitude_damping":
            gamma = kwargs.get("gamma", 0.1)
            rho = ch.apply_single_qubit_channel(rho, q_state, ch.kraus_amplitude_damping(gamma), n_qubits)
        elif channel_name == "phase_damping":
            lambda_p = kwargs.get("lambda", 0.1)
            rho = ch.apply_single_qubit_channel(rho, q_state, ch.kraus_phase_damping(lambda_p), n_qubits)
        elif channel_name == "thermal":
            p_ex = kwargs.get("p_ex", 0.1)
            rho = ch.apply_single_qubit_channel(rho, q_state, ch.kraus_thermal(p_ex), n_qubits)
        elif channel_name == "detector_loss":
            eta = kwargs.get("eta", 0.9)
            rho = ch.apply_single_qubit_channel(rho, q_state, ch.kraus_detector_loss(eta), n_qubits)
        else:
            raise ValueError(f"Unknown channel: {channel_name}")
    return rho


class NoiseModel:
    """
    Configurable noise: list of injections (when, channel, qubits, kwargs).
    'when' can be an int (step index after which to inject) or a string
    (e.g. 'after_bell_creation', 'before_readout').
    """

    def __init__(self, injections: list[dict[str, Any]] | None = None):
        self.injections = list(injections or [])

    def add(self, when: int | str, channel: str, qubits: list[int], **kwargs: Any) -> "NoiseModel":
        """Add one injection. when: step index or named point."""
        self.injections.append({"when": when, "channel": channel, "qubits": qubits, **kwargs})
        return self

    def injections_at_step(self, step: int) -> list[dict[str, Any]]:
        """Return injections that fire after the given step index."""
        out = []
        for inj in self.injections:
            w = inj["when"]
            if isinstance(w, int):
                if w == step:
                    out.append(inj)
            else:
                if INJECTION_AFTER_STEP.get(w, -1) == step:
                    out.append(inj)
        return out


def _average_fidelity_after_correction(
    rho_full: np.ndarray,
    msg_state: State,
    n: int = 3,
) -> float:
    """
    Average fidelity of Bob's state to |msg> after measuring qubits 0,1 and applying
    Z^m1 X^m2 to qubit 2. F = sum_{m1,m2} p(m1,m2) * <msg| U rho_2^{(m)} U^dag |msg>.
    """
    psi = np.asarray(msg_state.vec, dtype=np.complex128).ravel()
    total = 0.0
    # State index = q0*4 + q1*2 + q2 (qubit 0 MSB from product_state)
    for m1 in range(2):
        for m2 in range(2):
            # Outcome (m1, m2) on qubits 0,1: indices b and b+1 for qubit 2 in {0,1}
            b = 4 * m1 + 2 * m2
            idx = [b, b + 1]
            block = rho_full[np.ix_(idx, idx)]  # 2x2 block for qubit 2
            p = np.real(np.trace(block))
            if p < 1e-14:
                continue
            rho_2 = block / p
            # Bob applies Z^m1 X^m2 to undo (X^m2 Z^m1)|psi> -> |psi>
            U = np.linalg.matrix_power(_Z, m1) @ np.linalg.matrix_power(_X, m2)
            rho_corr = U @ rho_2 @ U.conj().T
            F = np.real(np.vdot(psi, rho_corr @ psi))
            total += p * F
    return total


def run_teleport_with_noise(
    msg_state: State,
    noise_model: NoiseModel | None = None,
) -> float:
    """
    Run teleportation in density-matrix form, applying noise at configured steps.
    Returns average fidelity of Bob's state (after measurement and correction) to the message.
    """
    if msg_state.n_qubits != 1:
        raise ValueError("msg_state must be 1 qubit")
    n = 3
    full = product_state(State(msg_state.vec, 1), "0", "0")
    d = DensityState.from_state(full)
    # Same gate sequence as teleportation.teleport_circuit
    gates = [(H, [1]), (CNOT, [1, 2]), (CNOT, [0, 1]), (H, [0])]
    for step, (gate, qubits) in enumerate(gates):
        d = d.apply_gate(gate, qubits)
        for inj in (noise_model or NoiseModel()).injections_at_step(step + 1):
            ch_name = inj["channel"]
            qubits_inj = inj["qubits"]
            kwargs = {k: v for k, v in inj.items() if k not in ("when", "channel", "qubits")}
            rho_new = _apply_channel_to_rho(d.rho, n, ch_name, qubits_inj, **kwargs)
            d = DensityState(rho_new, n)
    return _average_fidelity_after_correction(d.rho, msg_state, n)


def run_thief_with_noise(
    msg_state: State,
    thief_angle: float = 0.3,
    noise_model: NoiseModel | None = None,
) -> float:
    """
    Run tamper-evident teleport: circuit + optional thief Rx on qubit 2 + optional noise.
    Returns fidelity of Bob's state to original message.
    """
    if msg_state.n_qubits != 1:
        raise ValueError("msg_state must be 1 qubit")
    n = 3
    full = product_state(State(msg_state.vec, 1), "0", "0")
    d = DensityState.from_state(full)
    gates = [(H, [1]), (CNOT, [1, 2]), (CNOT, [0, 1]), (H, [0])]
    for step, (gate, qubits) in enumerate(gates):
        d = d.apply_gate(gate, qubits)
        for inj in (noise_model or NoiseModel()).injections_at_step(step + 1):
            ch_name = inj["channel"]
            qubits_inj = inj["qubits"]
            kwargs = {k: v for k, v in inj.items() if k not in ("when", "channel", "qubits")}
            rho_new = _apply_channel_to_rho(d.rho, n, ch_name, qubits_inj, **kwargs)
            d = DensityState(rho_new, n)
    # Thief: Rx(thief_angle) on Bob's qubit (protocol qubit 2 -> state qubit 0)
    from .tamper_evident import _rx
    d = d.apply_gate(_rx(thief_angle), [PROTOCOL_TO_STATE_QUBIT[2]])
    return _average_fidelity_after_correction(d.rho, msg_state, n)
