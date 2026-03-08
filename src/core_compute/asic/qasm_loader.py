"""
Load OpenQASM 2/3 source and map to ASIC op list (Op) for circuit.py and pulse compiler.
Ref: NEXT_STEPS_ROADMAP.md §4.1 OpenQASM 3.0 / QIR Integration.
Also provides interaction graph extraction for Algorithm-to-ASIC pipeline.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import networkx as nx

from .circuit import Op
from .gate_set import DEFAULT_GATE_SET, GateSet


class QasmParseError(ValueError):
    """Raised when QASM parse or validation fails. Optional line number for editor underlining."""
    def __init__(self, message: str, line: int | None = None):
        super().__init__(message)
        self.line = line


# ASIC-supported gates: H, X, Z, CNOT, Rx(theta)
_SUPPORTED_1Q = {"h", "x", "z"}
_SUPPORTED_1Q_PARAM = {"rx"}
_SUPPORTED_2Q = {"cx", "cnot"}


def _strip_line_comment(s: str) -> str:
    """Remove // and rest of line (OpenQASM 2 style)."""
    i = s.find("//")
    if i >= 0:
        s = s[:i].rstrip()
    return s.strip()


def _parse_qasm2_line(line: str) -> tuple[str, list[int], Any] | None:
    """Parse a single gate line (OpenQASM 2 style). Returns (gate, targets, param) or None."""
    line = _strip_line_comment(line.strip())
    if not line or line.startswith("OPENQASM") or line.startswith("include") or line.startswith("qreg") or line.startswith("creg") or line.startswith("barrier"):
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
    """Parse OpenQASM 2 text (no include) into list of Op. Reject unsupported gates. Raises QasmParseError with line number."""
    ops: list[Op] = []
    for line_no, line in enumerate(qasm_text.splitlines(), start=1):
        parsed = _parse_qasm2_line(line)
        if parsed is None:
            # Report line number for lines that look like statements but don't parse
            stripped = _strip_line_comment(line.strip())
            if stripped and (stripped.endswith(";") or "q[" in stripped):
                raise QasmParseError("Unrecognized or malformed line", line=line_no)
            continue
        gate, targets, param = parsed
        if gate in _SUPPORTED_1Q:
            ops.append(Op(gate=gate.upper(), targets=targets, param=None))
        elif gate in _SUPPORTED_1Q_PARAM and param is not None:
            ops.append(Op(gate="Rx", targets=targets, param=param))
        elif gate in _SUPPORTED_2Q and len(targets) == 2:
            ops.append(Op(gate="CNOT", targets=targets, param=None))
        else:
            raise QasmParseError(
                f"Unsupported or malformed gate: {gate} {targets} (ASIC supports H, X, Z, Rx, CNOT)",
                line=line_no,
            )
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
    """Load from string (OpenQASM 2 style, no include). Raises QasmParseError with line number on parse error."""
    return _qasm2_to_ops(qasm_text)


def interaction_graph_from_ops(ops: list[Op], gate_set: GateSet | None = None) -> nx.Graph:
    """
    Build an undirected interaction graph from a circuit op list.
    Nodes are qubit indices; an edge (u, v) exists if a 2-qubit gate acts on (u, v).
    Edge weight = number of 2-qubit gates between that pair.
    """
    gs = gate_set if gate_set is not None else DEFAULT_GATE_SET
    G: nx.Graph = nx.Graph()
    for op in ops:
        for q in op.targets:
            G.add_node(q)
        if len(op.targets) == 2 and gs.is_two_qubit(op.gate):
            u, v = min(op.targets[0], op.targets[1]), max(op.targets[0], op.targets[1])
            if G.has_edge(u, v):
                G.edges[u, v]["weight"] = G.edges[u, v].get("weight", 1) + 1
            else:
                G.add_edge(u, v, weight=1)
    return G


def interaction_graph_from_qasm_string(qasm_text: str) -> nx.Graph:
    """Parse QASM string to ops, then build interaction graph."""
    ops = load_qasm_string(qasm_text)
    return interaction_graph_from_ops(ops)


def interaction_graph_from_qasm_path(path: str) -> nx.Graph:
    """Load QASM file to ops, then build interaction graph."""
    ops = load_qasm(path)
    return interaction_graph_from_ops(ops)
