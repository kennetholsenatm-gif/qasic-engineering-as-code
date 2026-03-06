"""
Quantum ASIC topology: number of qubits and which pairs can interact (CNOT).
Minimal for our protocols: linear chain 0 - 1 - 2 (teleport + commitment).
"""
from __future__ import annotations


class Topology:
    """
    Fixed qubit count and allowed 2-qubit edges. Only adjacent pairs can run CNOT.
    Qubits are 0 .. n_qubits-1. Edges are undirected (control/target chosen per gate).
    """

    def __init__(self, n_qubits: int, edges: list[tuple[int, int]]):
        self._n = n_qubits
        self._edges = frozenset(tuple(sorted(e)) for e in edges)

    @property
    def n_qubits(self) -> int:
        return self._n

    @property
    def edges(self) -> frozenset[tuple[int, int]]:
        return self._edges

    def can_cnot(self, control: int, target: int) -> bool:
        """True if a CNOT(control, target) is allowed (edge exists)."""
        return (min(control, target), max(control, target)) in self._edges

    def neighbors(self, q: int) -> list[int]:
        """Qubits that share an edge with q."""
        out = []
        for a, b in self._edges:
            if a == q:
                out.append(b)
            elif b == q:
                out.append(a)
        return out

    def __repr__(self) -> str:
        return f"Topology(n={self._n}, edges={set(self._edges)})"


# Linear chain 0 - 1 - 2: supports teleport (0,1,2) and commitment (0,1)
DEFAULT_TOPOLOGY = Topology(
    n_qubits=3,
    edges=[(0, 1), (1, 2)],
)
