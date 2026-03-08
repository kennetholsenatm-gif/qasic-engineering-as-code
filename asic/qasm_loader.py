"""
Load OpenQASM 2/3 source and map to ASIC op list (Op) for circuit.py and pulse compiler.
Ref: NEXT_STEPS_ROADMAP.md §4.1 OpenQASM 3.0 / QIR Integration.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .circuit import Op


# ASIC-supported gates: H, X, Z, CNOT, Rx(theta)
_SUPPORTED_1Q = {"h", "x", "z"}
_SUPPORTED_1Q_PARAM = {"rx"}
_SUPPORTED_2Q = {"cx", "cnot"}


def _parse_qasm2_line(line: str) -> tuple[str, list[int], Any] | None:
    """Parse a single gate line (OpenQASM 2 style). Returns (gate, targets, param) or None."""
    line = line.strip()
    if not line or line.startswith("//") or line.startswith("OPENQASM") or line.startswith("include") or line.startswith("qreg") or line.startswith("creg"):
        return None
    # Gate: gate_name q[0], q[1]; or gate_name(angle) q[0];
    m = re.match(r"(\w+)\s*\(\s*([^)]+)\s*\)\s+q\[(\d+)\](?:\s*,\s*q\[(\d+)\])?;?", line, re.IGNORECASE)
    if m:
        gate, param_str, q0, q1 = m.group(1).lower(), m.group(2), int(m.group(3)), int(m.group(4)) if m.group(4) is not None else None
        param = None
        try:
            param = float(param_str)
        except ValueError:
            pass
        if q1 is not None:
            return (gate, [q0, q1], param)
        return (gate, [q0], param)
    m = re.match(r"(\w+)\s+q\[(\d+)\](?:\s*,\s*q\[(\d+)\])?;?", line, re.IGNORECASE)
    if m:
        gate, q0, q1 = m.group(1).lower(), int(m.group(2)), m.group(3)
        q1 = int(q1) if q1 is not None else None
        if q1 is not None:
            return (gate, [q0, q1], None)
        return (gate, [q0], None)
    return None


def _qasm2_to_ops(qasm_text: str) -> list[Op]:
    """Parse OpenQASM 2 text (no include) into list of Op. Reject unsupported gates."""
    ops: list[Op] = []
    for line in qasm_text.splitlines():
        parsed = _parse_qasm2_line(line)
        if parsed is None:
            continue
        gate, targets, param = parsed
        if gate in _SUPPORTED_1Q:
            ops.append(Op(gate=gate.upper(), targets=targets, param=None))
        elif gate in _SUPPORTED_1Q_PARAM and param is not None:
            ops.append(Op(gate="Rx", targets=targets, param=param))
        elif gate in _SUPPORTED_2Q and len(targets) == 2:
            ops.append(Op(gate="CNOT", targets=targets, param=None))
        else:
            raise ValueError(f"Unsupported or malformed gate: {gate} {targets} (ASIC supports H, X, Z, Rx, CNOT)")
    return ops


def load_qasm(path: str) -> list[Op]:
    """
    Load .qasm file and return list of Op compatible with asic.circuit.
    If qiskit.qasm2 is available, uses it; else uses a simple regex parser for OpenQASM 2.
    """
    try:
        from qiskit.qasm2 import load
        circuit = load(path)
        return _quantum_circuit_to_ops(circuit)
    except ImportError:
        pass
    except Exception:
        pass
    text = Path(path).read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if not line.strip().startswith("include")]
    return _qasm2_to_ops("\n".join(lines))


def _quantum_circuit_to_ops(circuit: Any) -> list[Op]:
    """Convert Qiskit QuantumCircuit to list of Op (H, X, Z, CNOT, Rx)."""
    ops: list[Op] = []
    for inst in circuit.data:
        name = inst.operation.name.lower()
        qubits = [circuit.find_bit(q).index for q in inst.qubits]
        param = None
        if hasattr(inst.operation, "params") and inst.operation.params:
            param = float(inst.operation.params[0]) if inst.operation.params else None
        if name == "h":
            ops.append(Op(gate="H", targets=qubits, param=None))
        elif name == "x":
            ops.append(Op(gate="X", targets=qubits, param=None))
        elif name == "z":
            ops.append(Op(gate="Z", targets=qubits, param=None))
        elif name == "rx" and param is not None:
            ops.append(Op(gate="Rx", targets=qubits, param=param))
        elif name in ("cx", "cnot") and len(qubits) == 2:
            ops.append(Op(gate="CNOT", targets=qubits, param=None))
        else:
            raise ValueError(f"Unsupported gate from QASM: {inst.operation.name} (ASIC: H, X, Z, Rx, CNOT)")
    return ops


def load_qasm_string(qasm_text: str) -> list[Op]:
    """Load from string (OpenQASM 2 style, no include)."""
    return _qasm2_to_ops(qasm_text)
