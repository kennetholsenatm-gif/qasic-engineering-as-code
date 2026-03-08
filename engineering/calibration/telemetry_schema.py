"""
Minimal schema for quantum device telemetry: per-qubit T1/T2, gate fidelities, phase offsets.
Used by the digital twin and Bayesian update to adjust decoherence and phase estimates.
"""
from __future__ import annotations

from typing import Any


QUANTUM_TELEMETRY_SCHEMA = {
    "description": "Quantum device telemetry for digital twin calibration",
    "type": "object",
    "properties": {
        "timestamp_iso": {"type": "string", "description": "ISO8601 timestamp"},
        "qubits": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "T1_us": {"type": "number", "description": "Relaxation time (microseconds)"},
                    "T2_us": {"type": "number", "description": "Dephasing time (microseconds)"},
                    "phase_offset_rad": {"type": "number", "description": "Phase drift from nominal"},
                },
            },
        },
        "gate_fidelities": {
            "type": "array",
            "description": "Optional: 1q or 2q gate fidelities",
            "items": {
                "type": "object",
                "properties": {
                    "gate": {"type": "string"},
                    "qubits": {"type": "array", "items": {"type": "integer"}},
                    "fidelity": {"type": "number"},
                },
            },
        },
        "aggregate": {
            "type": "object",
            "properties": {
                "mean_T1_us": {"type": "number"},
                "mean_T2_us": {"type": "number"},
                "drift_score": {"type": "number"},
            },
        },
    },
}


def validate_telemetry(data: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Lightweight validation: check required-ish keys and types.
    Returns (valid, list of error messages).
    """
    errors = []
    if not isinstance(data, dict):
        return False, ["Telemetry must be a dict"]
    if "qubits" in data:
        if not isinstance(data["qubits"], list):
            errors.append("qubits must be a list")
        else:
            for i, q in enumerate(data["qubits"]):
                if not isinstance(q, dict):
                    errors.append(f"qubits[{i}] must be a dict")
                else:
                    if "T1_us" in q and not isinstance(q["T1_us"], (int, float)):
                        errors.append(f"qubits[{i}].T1_us must be number")
                    if "T2_us" in q and not isinstance(q["T2_us"], (int, float)):
                        errors.append(f"qubits[{i}].T2_us must be number")
    return len(errors) == 0, errors
