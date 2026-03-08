"""
Quantum ASIC gate set: only the 1- and 2-qubit gates needed for the toy protocols.
No universal set—just H, X, Z, CNOT (and optional Rx for tamper model).
"""
from __future__ import annotations

from typing import Any

# Gate names that the ASIC supports
SINGLE_QUBIT_GATES = frozenset({"H", "X", "Z"})
PARAM_SINGLE_QUBIT_GATES = frozenset({"Rx"})  # Rx(angle)
TWO_QUBIT_GATES = frozenset({"CNOT"})


class GateSet:
    """Allowed gates: 1q = H, X, Z, [Rx], 2q = CNOT only."""

    def __init__(
        self,
        single_qubit: set[str] | None = None,
        param_single_qubit: set[str] | None = None,
        two_qubit: set[str] | None = None,
    ):
        self._1q = frozenset(single_qubit or SINGLE_QUBIT_GATES)
        self._1q_param = frozenset(param_single_qubit or PARAM_SINGLE_QUBIT_GATES)
        self._2q = frozenset(two_qubit or TWO_QUBIT_GATES)

    def is_single_qubit(self, name: str) -> bool:
        return name in self._1q or name in self._1q_param

    def is_parametrized(self, name: str) -> bool:
        return name in self._1q_param

    def is_two_qubit(self, name: str) -> bool:
        return name in self._2q

    def allowed(self, name: str) -> bool:
        return self.is_single_qubit(name) or self.is_two_qubit(name)

    def __repr__(self) -> str:
        return f"GateSet(1q={set(self._1q)}, 1q_param={set(self._1q_param)}, 2q={set(self._2q)})"


DEFAULT_GATE_SET = GateSet()
