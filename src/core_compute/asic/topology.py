"""
Quantum ASIC topology: number of qubits and which pairs can interact.
Uses a networkx.Graph for nodes/edges with optional physical and coupling attributes.
Supports can_execute(gate_type, control, target) and backward-compatible can_cnot.
"""
from __future__ import annotations

from typing import Any

import networkx as nx

# Two-qubit gate names that can be native on an edge (CNOT can be compiled from CZ).
_TWO_QUBIT_GATES = frozenset({"CNOT", "CZ", "iSWAP"})


class Topology:
    """
    Qubit topology as an undirected graph. Qubits are nodes 0 .. n_qubits-1.
    Edges may have coupling_j_mhz, native_gate (e.g. 'CZ', 'iSWAP').
    Nodes may have frequency_ghz, anharmonicity_mhz, t1_us, t2_us.
    """

    def __init__(
        self,
        n_qubits: int,
        edges: list[tuple[int, int] | tuple[int, int, dict[str, Any]]],
        *,
        node_attrs: dict[int, dict[str, Any]] | None = None,
    ):
        self._n = n_qubits
        self._g: nx.Graph = nx.Graph()
        self._g.add_nodes_from(range(n_qubits))
        if node_attrs:
            for q, attrs in node_attrs.items():
                if 0 <= q < n_qubits:
                    self._g.nodes[q].update(attrs)

        for e in edges:
            if len(e) == 2:
                a, b = e
                self._g.add_edge(a, b)
            else:
                a, b, attrs = e
                self._g.add_edge(a, b, **attrs)

    @property
    def n_qubits(self) -> int:
        return self._n

    @property
    def edges(self) -> frozenset[tuple[int, int]]:
        """Backward-compatible: frozenset of (min, max) for each edge."""
        return frozenset((min(u, v), max(u, v)) for u, v in self._g.edges())

    def can_execute(self, gate_type: str, control: int, target: int) -> bool:
        """
        True if gate_type can be executed on the given qubits.
        Single-qubit: any qubit in [0, n_qubits). Two-qubit: edge must exist and
        native_gate (if set) must match or support the gate (CNOT allowed if native is CZ/CNOT).
        """
        if control < 0 or control >= self._n or target < 0 or target >= self._n:
            return False
        if control == target:
            return False
        # Single-qubit: no edge needed
        if gate_type not in _TWO_QUBIT_GATES:
            return True
        # Two-qubit: need edge
        u, v = min(control, target), max(control, target)
        if not self._g.has_edge(u, v):
            return False
        data = self._g.edges[u, v]
        native = data.get("native_gate")
        if native is None:
            return True
        if gate_type == native:
            return True
        if native == "CZ" and gate_type == "CNOT":
            return True
        if native == "CNOT" and gate_type == "CNOT":
            return True
        return False

    def can_cnot(self, control: int, target: int) -> bool:
        """True if CNOT(control, target) is allowed (edge exists and supports CNOT)."""
        return self.can_execute("CNOT", control, target)

    def neighbors(self, q: int) -> list[int]:
        """Qubits that share an edge with q."""
        if q < 0 or q >= self._n:
            return []
        return list(self._g.neighbors(q))

    def __repr__(self) -> str:
        return f"Topology(n={self._n}, edges={set(self.edges)})"


# Reference topology for validation/demos only. Production ASIC topology is built from
# openQASM via interaction_graph -> build_topology_from_interaction_graph (qasm_to_asic).
# Linear chain 0 - 1 - 2: supports teleport (0,1,2) and commitment (0,1)
DEFAULT_TOPOLOGY = Topology(
    n_qubits=3,
    edges=[(0, 1), (1, 2)],
)
