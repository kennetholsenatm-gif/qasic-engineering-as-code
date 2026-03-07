"""
Named logical topologies for protocol and QUBO routing.
Provides linear chain, star, and repeater chain; exports Topology and
interaction_matrix for use with routing_qubo_qaoa.build_routing_qubo().
Ref: Whitepaper star topology for multi-node entanglement; multi-hop repeater chains.
"""
from __future__ import annotations

import numpy as np
from typing import TYPE_CHECKING

from .topology import Topology

if TYPE_CHECKING:
    pass


def edges_to_interaction_matrix(edges: list[tuple[int, int]], n_qubits: int) -> np.ndarray:
    """
    Convert a list of undirected edges to an n×n symmetric interaction matrix
    (adjacency matrix). Used by the QUBO solver to penalize logical pairs that
    must interact when placed on distant physical nodes.
    """
    mat = np.zeros((n_qubits, n_qubits), dtype=float)
    for a, b in edges:
        if 0 <= a < n_qubits and 0 <= b < n_qubits and a != b:
            mat[a, b] = 1
            mat[b, a] = 1
    return mat


def linear_chain(n_qubits: int) -> tuple[Topology, np.ndarray]:
    """
    Linear chain: 0 - 1 - 2 - ... - (n-1). Edges (i, i+1).
    Default for teleportation (3 qubits).
    """
    if n_qubits < 2:
        raise ValueError("linear_chain requires n_qubits >= 2")
    edges = [(i, i + 1) for i in range(n_qubits - 1)]
    topo = Topology(n_qubits=n_qubits, edges=edges)
    interaction = edges_to_interaction_matrix(edges, n_qubits)
    return topo, interaction


def star(n_qubits: int, hub: int = 0) -> tuple[Topology, np.ndarray]:
    """
    Star topology: one hub connected to all others. Default hub = 0.
    Edges (hub, i) for all i != hub. For multi-node entanglement distribution.
    """
    if n_qubits < 2:
        raise ValueError("star requires n_qubits >= 2")
    if not 0 <= hub < n_qubits:
        raise ValueError("hub must be in [0, n_qubits)")
    edges = [(hub, i) for i in range(n_qubits) if i != hub]
    topo = Topology(n_qubits=n_qubits, edges=edges)
    interaction = edges_to_interaction_matrix(edges, n_qubits)
    return topo, interaction


def repeater_chain(n_qubits: int) -> tuple[Topology, np.ndarray]:
    """
    Multi-hop repeater chain: same as linear chain 0 - 1 - ... - (n-1).
    Use for repeater links along a line.
    """
    return linear_chain(n_qubits)


# Registry of named topologies for CLI and viz
NAMED_TOPOLOGIES = {
    "linear": linear_chain,
    "linear_chain": linear_chain,
    "star": star,
    "repeater": repeater_chain,
    "repeater_chain": repeater_chain,
}


def get_topology(name: str, n_qubits: int, **kwargs: int) -> tuple[Topology, np.ndarray]:
    """
    Get (Topology, interaction_matrix) for a named topology.
    name: 'linear', 'linear_chain', 'star', 'repeater', 'repeater_chain'.
    kwargs: passed to the topology builder (e.g. hub=0 for star).
    """
    if name not in NAMED_TOPOLOGIES:
        raise ValueError(
            f"Unknown topology {name!r}. Choose from: {sorted(set(NAMED_TOPOLOGIES.keys()))}"
        )
    fn = NAMED_TOPOLOGIES[name]
    if name == "star":
        return fn(n_qubits, hub=kwargs.get("hub", 0))
    return fn(n_qubits)
