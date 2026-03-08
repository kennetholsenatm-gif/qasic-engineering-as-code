"""
3-qubit bit-flip repetition code: encode one logical qubit, correct one bit-flip error.
Uses ASIC linear chain 0—1—2; data on qubit 1. Syndrome inferred from state for demo.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

if str(Path(__file__).resolve().parents[1]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from state import State, product_state
from state.gates import X, CNOT
from asic.circuit import protocol_bitflip_code_ops, Op
from asic.executor import run_asic_circuit


def _syndrome_from_state(state: State) -> tuple[int, int]:
    """
    From 3-qubit state, return (s01, s12) where s_ab = parity(qubit_a, qubit_b).
    For a computational basis state |b0 b1 b2>, s01 = (b0+b1)%2, s12 = (b1+b2)%2.
    """
    vec = state.vec.ravel()
    n = state.n_qubits
    if n != 3:
        raise ValueError("Expected 3 qubits")
    # Find dominant basis state (for pure state after error we are in one basis state)
    idx = int(np.argmax(np.abs(vec) ** 2))
    b0 = (idx >> 0) & 1
    b1 = (idx >> 1) & 1
    b2 = (idx >> 2) & 1
    s01 = (b0 + b1) % 2
    s12 = (b1 + b2) % 2
    return s01, s12


def _correction_qubit(s01: int, s12: int) -> int | None:
    """Return qubit index to apply X for correction: (1,0)->0, (0,1)->2, (1,1)->1."""
    if s01 == 1 and s12 == 0:
        return 0
    if s01 == 0 and s12 == 1:
        return 2
    if s01 == 1 and s12 == 1:
        return 1
    return None  # no error (00)


def decode_ops() -> list[Op]:
    """Same as encode: CNOT 1->0, CNOT 1->2 (self-inverse)."""
    return [Op("CNOT", [1, 0]), Op("CNOT", [1, 2])]


def run_bitflip_code(
    logical_bit: int,
    error_qubit: int,
    *,
    seed: int | None = None,
) -> dict:
    """
    Encode logical_bit (0 or 1), apply single bit-flip on error_qubit (0, 1, or 2),
    infer syndrome, correct, decode; return success and fidelity info.
    """
    if logical_bit not in (0, 1):
        raise ValueError("logical_bit must be 0 or 1")
    if error_qubit not in (0, 1, 2):
        raise ValueError("error_qubit must be 0, 1, or 2")

    # Initial: |0 d 0> with d = logical_bit on qubit 1
    d = "1" if logical_bit else "0"
    initial = product_state("0", d, "0")

    # Encode + error
    ops_encode_error = protocol_bitflip_code_ops(include_error_qubit=error_qubit)
    state = run_asic_circuit(initial, ops_encode_error)

    # Syndrome and correction
    s01, s12 = _syndrome_from_state(state)
    correct_q = _correction_qubit(s01, s12)
    if correct_q is not None:
        state = state.apply(X, [correct_q])

    # Decode (same CNOTs)
    state = run_asic_circuit(state, decode_ops())

    # Read logical qubit (qubit 1): probability of |1>
    vec = state.vec.ravel()
    p1 = 0.0
    for i in range(8):
        if (i >> 1) & 1:  # qubit 1 is 1
            p1 += float(np.abs(vec[i]) ** 2)
    decoded_bit = 1 if p1 > 0.5 else 0
    success = decoded_bit == logical_bit
    fidelity = p1 if logical_bit == 1 else (1.0 - p1)

    return {
        "logical_bit": logical_bit,
        "error_qubit": error_qubit,
        "syndrome": (s01, s12),
        "corrected_qubit": correct_q,
        "decoded_bit": decoded_bit,
        "success": success,
        "fidelity": fidelity,
    }
