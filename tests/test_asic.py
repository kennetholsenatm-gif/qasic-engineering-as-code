"""Tests for asic.circuit (validate_circuit, protocol_*_ops) and asic.executor (run_asic_circuit)."""
from __future__ import annotations

import numpy as np
import pytest

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
