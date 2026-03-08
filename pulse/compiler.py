"""
Compile ASIC circuit (gate list) to a pulse schedule.
Input: ASIC circuit (list of Op) + backend config (topology, calibration).
Output: OpenPulse Schedule or pseudo-schedule dict when Qiskit not available.
"""
from __future__ import annotations

from typing import Any

# Avoid hard import of asic so pulse can be tested standalone with mocks
try:
    from asic.circuit import Op
    from asic.topology import Topology
    _HAS_ASIC = True
except ImportError:
    Op = None
    Topology = None
    _HAS_ASIC = False


def compile_circuit_to_schedule(
    ops: list[Any],
    backend_config: dict[str, Any],
    topology: Any = None,
) -> Any:
    """
    Compile a list of gate ops to a pulse schedule.
    ops: list of objects with .gate, .targets, .param (e.g. asic.circuit.Op).
    backend_config: dict with "qubits" (list of channel configs), optional "dt", "name".
    topology: optional Topology for edge checks; if None, assume linear chain from config.
    Returns: qiskit.pulse.Schedule when qiskit is available, else a dict (pseudo-schedule).
    """
    try:
        from .openpulse_backend import build_schedule_openpulse
        return build_schedule_openpulse(ops, backend_config, topology)
    except ImportError:
        from .pseudo_schedule import build_pseudo_schedule
        return build_pseudo_schedule(ops, backend_config)
