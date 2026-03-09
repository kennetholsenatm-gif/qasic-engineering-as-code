"""
Load OpenQASM 2/3 source and map to ASIC op list (Op) for circuit.py and pulse compiler.
Ref: NEXT_STEPS_ROADMAP.md §4.1 OpenQASM 3.0 / QIR Integration.
Also provides interaction graph extraction for Algorithm-to-ASIC pipeline.

OpenQASM 2.0: parsed via regex or qiskit.qasm2 when available.
OpenQASM 3.0: parsed via qiskit.qasm3.loads/load when qiskit-qasm3-import is installed.
Version is detected from the first declaration line (OPENQASM 2.0; vs OPENQASM 3.0;).

Barrier: OpenQASM 2/3 barrier statements are supported and ignored when building the op list
(they are a directive with no logical effect on the ASIC circuit).
Measure: OpenQASM 2/3 measure statements are accepted as part of the circuit and skipped when
building the op list (measurement is classical; the ASIC op list contains only quantum gates).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import networkx as nx

from .circuit import Op
from .gate_set import DEFAULT_GATE_SET, GateSet

# OpenQASM version declaration pattern (first line or early in file)
_OPENQASM_VERSION_RE = re.compile(r"OPENQASM\s+(\d+\.\d+)", re.IGNORECASE)


def _detect_qasm_version(qasm_text: str) -> str:
    """
    Detect OpenQASM version from source (OPENQASM 2.0; or OPENQASM 3.0;).
    Returns "2.0" or "3.0". Defaults to "2.0" if no declaration found for backward compatibility.
    """
    for line in qasm_text.splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        m = _OPENQASM_VERSION_RE.search(line)
        if m:
            ver = m.group(1)
            if ver.startswith("3"):
                return "3.0"
            if ver.startswith("2"):
                return "2.0"
            raise QasmParseError(f"Unsupported OPENQASM version: {ver} (supported: 2.0, 3.0)")
        break
    return "2.0"


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
    if not line or line.startswith("OPENQASM") or line.startswith("include") or line.startswith("qreg") or line.startswith("creg") or line.startswith("barrier") or line.startswith("measure"):
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
            # Skip declaration/header lines; report only truly unrecognized lines
            stripped = _strip_line_comment(line.strip())
            if stripped and (stripped.endswith(";") or "q[" in stripped):
                if stripped.startswith(("qreg", "creg", "OPENQASM", "include", "barrier", "gate", "opaque", "measure")):
                    continue
                raise QasmParseError("Unrecognized or malformed line", line=line_no)
            continue
        gate, targets, param = parsed
        if gate == "measure":
            continue  # Measurement is part of the circuit but does not add a quantum gate to the ASIC op list
        if gate in _SUPPORTED_1Q:
            ops.append(Op(gate=gate.upper(), targets=targets, param=None))
        elif gate in _SUPPORTED_1Q_PARAM and param is not None:
            ops.append(Op(gate="Rx", targets=targets, param=param))
        elif gate in _SUPPORTED_2Q and len(targets) == 2:
            ops.append(Op(gate="CNOT", targets=targets, param=None))
        else:
            raise QasmParseError(
                f"Unsupported or malformed gate: {gate} {targets} (ASIC supports H, X, Z, Rx, CNOT; measure is accepted and skipped for op list)",
                line=line_no,
            )
    return ops


# ASIC basis for Qiskit transpiler (decomposition)
_ASIC_BASIS_GATES = ["h", "x", "z", "rx", "cx"]


def _transpile_to_asic_basis(circuit: Any) -> Any:
    """
    Transpile a Qiskit QuantumCircuit to ASIC basis gates (H, X, Z, Rx, CX).
    Enables decomposition of T, S, Rz, Ry, U2, U3, etc. when decompose_to_asic=True.
    """
    from qiskit import transpile
    return transpile(circuit, basis_gates=_ASIC_BASIS_GATES, optimization_level=1)


def _qasm3_to_ops_via_qiskit(qasm_text: str, *, decompose_to_asic: bool = False) -> list[Op]:
    """
    Parse OpenQASM 3.0 source via qiskit.qasm3.loads and convert to ASIC Op list.
    Requires qiskit-qasm3-import. If decompose_to_asic is True, transpiles to H, X, Z, Rx, CX first.
    """
    try:
        from qiskit.qasm3 import loads as qasm3_loads
    except ImportError as e:
        raise QasmParseError(
            "OpenQASM 3.0 parsing requires qiskit-qasm3-import. "
            "Install with: pip install qiskit-qasm3-import"
        ) from e
    try:
        circuit = qasm3_loads(qasm_text)
        if decompose_to_asic:
            circuit = _transpile_to_asic_basis(circuit)
        return _quantum_circuit_to_ops(circuit)
    except ValueError as e:
        raise QasmParseError(str(e)) from e


def _qasm3_to_ops_from_path(path: str, *, decompose_to_asic: bool = False) -> list[Op]:
    """Load OpenQASM 3.0 from file path via qiskit.qasm3.load. Optional decomposition to ASIC basis."""
    try:
        from qiskit.qasm3 import load as qasm3_load
    except ImportError as e:
        raise QasmParseError(
            "OpenQASM 3.0 parsing requires qiskit-qasm3-import. "
            "Install with: pip install qiskit-qasm3-import"
        ) from e
    try:
        circuit = qasm3_load(path)
        if decompose_to_asic:
            circuit = _transpile_to_asic_basis(circuit)
        return _quantum_circuit_to_ops(circuit)
    except ValueError as e:
        raise QasmParseError(str(e)) from e


def load_qasm(path: str, *, decompose_to_asic: bool = False) -> list[Op]:
    """
    Load .qasm file and return list of Op compatible with asic.circuit.
    Version is auto-detected: OPENQASM 3.0 uses qiskit.qasm3.load (requires qiskit-qasm3-import);
    OPENQASM 2.0 uses qiskit.qasm2 if available, else the built-in regex parser.
    When decompose_to_asic is True (and Qiskit is used), T, S, Rz, U3, etc. are decomposed to H, X, Z, Rx, CNOT.
    """
    text = Path(path).read_text(encoding="utf-8")
    version = _detect_qasm_version(text)
    if version == "3.0":
        return _qasm3_to_ops_from_path(path, decompose_to_asic=decompose_to_asic)
    try:
        from qiskit.qasm2 import load
        circuit = load(path)
        if decompose_to_asic:
            circuit = _transpile_to_asic_basis(circuit)
        return _quantum_circuit_to_ops(circuit)
    except ImportError:
        pass
    except Exception:
        pass
    lines = [line for line in text.splitlines() if not line.strip().startswith("include")]
    return _qasm2_to_ops("\n".join(lines))


def _quantum_circuit_to_ops(circuit: Any) -> list[Op]:
    """Convert Qiskit QuantumCircuit to list of Op (H, X, Z, CNOT, Rx). Skips barrier and measure (directives/classical; no quantum gate for ASIC op list)."""
    ops: list[Op] = []
    for inst in circuit.data:
        name = inst.operation.name.lower()
        if name == "barrier":
            continue  # OpenQASM 2/3 directive; no-op for ASIC op list
        if name == "measure":
            continue  # Measurement is part of the circuit but does not add a quantum gate to the ASIC op list
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


def load_qasm_string(qasm_text: str, *, decompose_to_asic: bool = False) -> list[Op]:
    """
    Load from string. Version is auto-detected (OPENQASM 2.0 vs 3.0).
    OpenQASM 3.0 requires qiskit-qasm3-import. When decompose_to_asic is True (3.0 only),
    gates like T, S, Rz, U3 are decomposed to H, X, Z, Rx, CNOT. Raises QasmParseError on parse error.
    """
    version = _detect_qasm_version(qasm_text)
    if version == "3.0":
        return _qasm3_to_ops_via_qiskit(qasm_text, decompose_to_asic=decompose_to_asic)
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


def interaction_graph_from_qasm_string(qasm_text: str, *, decompose_to_asic: bool = False) -> nx.Graph:
    """Parse QASM string to ops, then build interaction graph. Optional decompose_to_asic for 3.0."""
    ops = load_qasm_string(qasm_text, decompose_to_asic=decompose_to_asic)
    return interaction_graph_from_ops(ops)


def interaction_graph_from_qasm_path(path: str, *, decompose_to_asic: bool = False) -> nx.Graph:
    """Load QASM file to ops, then build interaction graph. Optional decompose_to_asic when using Qiskit."""
    ops = load_qasm(path, decompose_to_asic=decompose_to_asic)
    return interaction_graph_from_ops(ops)
