"""
Named logical topologies for protocol and QUBO routing.
Provides linear chain, star, and repeater chain; exports Topology and
interaction_matrix for use with routing_qubo_qaoa.build_routing_qubo().
Also builds Topology and geometry manifest from an interaction graph (Algorithm-to-ASIC).
Ref: Whitepaper star topology for multi-node entanglement; multi-hop repeater chains.
"""
from __future__ import annotations

import numpy as np
from typing import Any

import networkx as nx

from .topology import Topology


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


def build_topology_from_interaction_graph(graph: nx.Graph) -> Topology:
    """
    Build a Topology from an interaction graph (e.g. from interaction_graph_from_ops).
    Nodes are remapped to 0..n-1 if not contiguous. Edges get optional weight attribute.
    """
    if graph.number_of_nodes() == 0:
        return Topology(n_qubits=0, edges=[])
    nodes = sorted(graph.nodes())
    n = len(nodes)
    node_to_idx = {q: i for i, q in enumerate(nodes)}
    edges: list[tuple[int, int] | tuple[int, int, dict[str, Any]]] = []
    for u, v in graph.edges():
        i, j = node_to_idx[u], node_to_idx[v]
        ii, jj = min(i, j), max(i, j)
        data = graph.edges.get((u, v), graph.edges.get((v, u), {}))
        w = data.get("weight")
        if w is not None:
            edges.append((ii, jj, {"weight": w}))
        else:
            edges.append((ii, jj))
    return Topology(n_qubits=n, edges=edges)


def _place_nodes_on_grid(graph: nx.Graph, nodes: list[int]) -> dict[int, tuple[int, int]]:
    """
    Place graph nodes on a 2D grid so that every edge is between grid-adjacent cells.
    Returns node_id -> (i, j). Uses BFS per component; unplaced nodes get next free cell.
    """
    coord: dict[int, tuple[int, int]] = {}
    used: set[tuple[int, int]] = set()

    def next_free_cell() -> tuple[int, int]:
        for si in range(20):
            for sj in range(20):
                c = (si, sj)
                if c not in used:
                    return c
        return (len(used) // 20, len(used) % 20)

    if not nodes:
        return coord
    while len(coord) < len(nodes):
        start = next(n for n in nodes if n not in coord)
        coord[start] = (0, 0) if not used else next_free_cell()
        used.add(coord[start])
        queue = [start]
        while queue:
            u = queue.pop(0)
            iu, ju = coord[u]
            for v in graph.neighbors(u):
                if v in coord:
                    continue
                for di, dj in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    cand = (iu + di, ju + dj)
                    if cand not in used:
                        coord[v] = cand
                        used.add(cand)
                        queue.append(v)
                        break
                else:
                    coord[v] = next_free_cell()
                    used.add(coord[v])
                    queue.append(v)
    return coord


def geometry_manifest_from_interaction_graph(
    graph: nx.Graph, pitch_um: float = 1.0
) -> dict[str, Any]:
    """
    Produce a geometry manifest (cells with i, j, phase_rad, dimension) so that
    superconducting_extraction only creates trace edges where the interaction graph has edges.
    Places qubits on a 2D grid via _place_nodes_on_grid; each node becomes one cell.
    """
    if graph.number_of_nodes() == 0:
        return {
            "pitch_um": pitch_um,
            "units": "um",
            "library_source": "qasm_to_asic",
            "shape": [0, 0],
            "num_cells": 0,
            "cells": [],
        }
    nodes = sorted(graph.nodes())
    coord = _place_nodes_on_grid(graph, nodes)
    cells: list[dict[str, Any]] = []
    for q in nodes:
        i, j = coord[q]
        cells.append({
            "i": i,
            "j": j,
            "phase_rad": 0.0,
            "dimension": 0.5,
        })
    max_i = max(c["i"] for c in cells)
    max_j = max(c["j"] for c in cells)
    return {
        "pitch_um": pitch_um,
        "units": "um",
        "library_source": "qasm_to_asic",
        "shape": [max_i + 1, max_j + 1],
        "num_cells": len(cells),
        "cells": cells,
    }


def routing_json_from_topology(topo: Topology, circuit_name: str) -> dict[str, Any]:
    """Optional routing JSON for extraction (num_physical_nodes)."""
    return {
        "num_physical_nodes": topo.n_qubits,
        "source": "qasm_to_asic",
        "circuit_name": circuit_name,
    }


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
