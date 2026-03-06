"""
Execute an ASIC circuit (list of Op) on a State. Proves the minimal gate set and
topology are sufficient to run the protocols.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# Allow running from project root or from asic/
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from state import State
from state.gates import H, X, Z, CNOT
from .circuit import Op


def _rx_matrix(angle: float) -> np.ndarray:
    c = np.cos(angle / 2)
    s = -1j * np.sin(angle / 2)
    return np.array([[c, s], [s, c]], dtype=np.complex128)


_GATE_MATRICES = {
    "H": H,
    "X": X,
    "Z": Z,
    "CNOT": CNOT,
}


def apply_op(state: State, op: Op) -> State:
    """Apply a single ASIC op to state. state is mutated conceptually via return."""
    if op.gate in _GATE_MATRICES:
        mat = _GATE_MATRICES[op.gate]
    elif op.gate == "Rx":
        if op.param is None:
            raise ValueError("Rx requires param (angle)")
        mat = _rx_matrix(float(op.param))
    else:
        raise ValueError(f"Unknown gate for execution: {op.gate}")
    return state.apply(mat, op.targets)


def run_asic_circuit(initial: State, ops: list[Op]) -> State:
    """Run a sequence of ASIC ops on initial state; return final state."""
    state = initial.copy()
    for op in ops:
        state = apply_op(state, op)
    return state


if __name__ == "__main__":
    from state import product_state
    from .circuit import protocol_teleport_ops

    # |psi>|0>|0> with |psi> = |+>
    psi = State(np.array([1, 1], dtype=np.complex128).reshape(-1, 1) / np.sqrt(2), 1)
    initial = product_state(psi, "0", "0")
    ops = protocol_teleport_ops()
    final = run_asic_circuit(initial, ops)
    print("Teleport ASIC circuit: 3-qubit state after 4 ops.")
    print("Bob's qubit (2) should be |+> after measurement + correction (not applied here).")
