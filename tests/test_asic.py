"""Tests for asic.circuit (validate_circuit, protocol_*_ops) and asic.executor (run_asic_circuit)."""
from __future__ import annotations

import importlib.util

import numpy as np
import pytest

HAVE_QASM3 = importlib.util.find_spec("qiskit.qasm3") is not None

from src.core_compute.state import State, product_state
from src.core_compute.asic.circuit import (
    validate_circuit,
    Op,
    protocol_teleport_ops,
    protocol_commitment_ops,
    protocol_thief_ops,
    ASICCircuit,
)
from src.core_compute.asic.executor import run_asic_circuit, apply_op


def test_validate_circuit_teleport_ops_valid():
    ops = protocol_teleport_ops()
    errors = validate_circuit(ops)
    assert errors == []


def test_validate_circuit_commitment_ops_valid():
    ops = protocol_commitment_ops()
    errors = validate_circuit(ops)
    assert errors == []


def test_validate_circuit_thief_ops_valid():
    ops = protocol_thief_ops(qubit=2, angle=0.3)
    errors = validate_circuit(ops)
    assert errors == []


def test_validate_circuit_rejects_unknown_gate():
    errors = validate_circuit([Op("UNKNOWN", [0])])
    assert len(errors) >= 1
    assert "unknown gate" in errors[0].lower()


def test_validate_circuit_rejects_cnot_on_non_edge():
    # Default topology is linear 0-1-2; CNOT(0, 2) not allowed
    errors = validate_circuit([Op("CNOT", [0, 2])])
    assert len(errors) >= 1
    assert "not allowed" in errors[0] or "no edge" in errors[0].lower()


def test_qasm_loader_string():
    """OpenQASM loader: parse string to Op list (H, X, Z, CNOT, Rx)."""
    from src.core_compute.asic.qasm_loader import load_qasm_string
    qasm = "h q[0];\nx q[1];\ncx q[0], q[1];\nz q[0];"
    ops = load_qasm_string(qasm)
    assert len(ops) == 4
    assert ops[0].gate == "H" and ops[0].targets == [0]
    assert ops[1].gate == "X" and ops[1].targets == [1]
    assert ops[2].gate == "CNOT" and ops[2].targets == [0, 1]
    assert ops[3].gate == "Z" and ops[3].targets == [0]


def test_detect_qasm_version():
    """Version detection: OPENQASM 2.0 vs 3.0 from first declaration."""
    from src.core_compute.asic.qasm_loader import _detect_qasm_version, QasmParseError
    assert _detect_qasm_version("OPENQASM 2.0;\ninclude \"qelib1.inc\";") == "2.0"
    assert _detect_qasm_version("OPENQASM 3.0;\ninclude \"stdgates.inc\";") == "3.0"
    assert _detect_qasm_version("  OPENQASM 3.0;") == "3.0"
    assert _detect_qasm_version("// comment\nOPENQASM 2.0;") == "2.0"
    assert _detect_qasm_version("h q[0];") == "2.0"
    with pytest.raises(QasmParseError, match="Unsupported OPENQASM version"):
        _detect_qasm_version("OPENQASM 1.0;")


@pytest.mark.skipif(not HAVE_QASM3, reason="qiskit-qasm3-import not installed")
def test_qasm_loader_string_openqasm3():
    """OpenQASM 3.0: parse string to Op list when qiskit.qasm3 is available."""
    from src.core_compute.asic.qasm_loader import load_qasm_string, interaction_graph_from_qasm_string
    qasm3 = """OPENQASM 3.0;
include "stdgates.inc";
qubit[3] q;
h q[0];
x q[1];
cx q[0], q[1];
z q[0];
"""
    ops = load_qasm_string(qasm3)
    assert len(ops) == 4
    assert ops[0].gate == "H" and ops[0].targets == [0]
    assert ops[2].gate == "CNOT" and ops[2].targets == [0, 1]
    G = interaction_graph_from_qasm_string(qasm3)
    assert G.number_of_nodes() >= 2
    assert G.has_edge(0, 1)


@pytest.mark.skipif(not HAVE_QASM3, reason="qiskit-qasm3-import not installed")
def test_qasm_loader_decompose_to_asic():
    """Optional decomposition: Rz/T/S/U3 etc. decomposed to H, X, Z, Rx, CNOT."""
    from src.core_compute.asic.qasm_loader import load_qasm_string
    # Rz is not in ASIC set; with decompose_to_asic=True it should be transpiled to basis
    qasm3_with_rz = """OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;
h q[0];
rz(0.5) q[0];
cx q[0], q[1];
"""
    ops = load_qasm_string(qasm3_with_rz, decompose_to_asic=True)
    assert len(ops) >= 2
    gates_used = {op.gate for op in ops}
    assert gates_used <= {"H", "X", "Z", "Rx", "CNOT"}


def test_run_asic_circuit_teleport():
    psi = State(np.array([1, 1], dtype=np.complex128).reshape(-1, 1) / np.sqrt(2), 1)
    initial = product_state(psi, "0", "0")
    ops = protocol_teleport_ops()
    final = run_asic_circuit(initial, ops)
    assert final.n_qubits == 3


def test_apply_op_rx_requires_param():
    from src.core_compute.asic.circuit import Op
    state = product_state("0", "0")
    with pytest.raises(ValueError, match="Rx requires param"):
        apply_op(state, Op("Rx", [0]))  # param=None


def test_interaction_graph_from_ops():
    """Interaction graph: nodes = qubits, edges = 2q gates, weight = count."""
    from src.core_compute.asic.qasm_loader import interaction_graph_from_ops
    ops = [
        Op("H", [0]),
        Op("CNOT", [0, 1]),
        Op("CNOT", [1, 2]),
        Op("CNOT", [0, 1]),
    ]
    G = interaction_graph_from_ops(ops)
    assert G.number_of_nodes() == 3
    assert G.number_of_edges() == 2  # (0,1) and (1,2); (0,1) has weight 2
    assert G.has_edge(0, 1) and G.has_edge(1, 2)
    assert G.edges[0, 1].get("weight") == 2
    assert G.edges[1, 2].get("weight") == 1


def test_build_topology_from_interaction_graph():
    """Topology from interaction graph: n_qubits and can_cnot on edges."""
    import networkx as nx
    from src.core_compute.asic.topology_builder import build_topology_from_interaction_graph
    G = nx.Graph()
    G.add_edges_from([(0, 1), (1, 2)])
    topo = build_topology_from_interaction_graph(G)
    assert topo.n_qubits == 3
    assert topo.can_cnot(0, 1) and topo.can_cnot(1, 2)
    assert not topo.can_cnot(0, 2)
