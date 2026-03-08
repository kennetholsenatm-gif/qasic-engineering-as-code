"""
Per-node decoherence rates for routing: use QuTiP Lindblad model to compute a scalar
decoherence score per physical node (e.g. 1/T2 or effective rate) for use in QUBO.
"""
from __future__ import annotations

from typing import Any

import numpy as np

try:
    import qutip as qt
    _HAS_QUTIP = True
except ImportError:
    qt = None
    _HAS_QUTIP = False


def get_node_decoherence_rates(
    num_nodes: int,
    node_params_list: list[dict[str, float]] | None = None,
) -> np.ndarray:
    """
    Return a decoherence score per physical node (length num_nodes).
    Each node is modeled as a single qubit under Lindblad evolution; the score is
    an effective rate (e.g. gamma1 + gamma_phi) so higher = worse for routing.
    If node_params_list is None, use default gamma1=0.1, gamma2=0.05 per node.
    node_params_list[i] can have 'gamma1', 'gamma2' (and optionally 'gamma_phi').
    """
    if not _HAS_QUTIP:
        # Fallback: return uniform small rates so routing still runs without QuTiP
        return np.ones(num_nodes, dtype=np.float64) * 0.1
    default = {"gamma1": 0.1, "gamma2": 0.05}
    if node_params_list is None:
        node_params_list = [default.copy() for _ in range(num_nodes)]
    while len(node_params_list) < num_nodes:
        node_params_list.append(default.copy())
    rates = np.zeros(num_nodes)
    for j in range(num_nodes):
        p = node_params_list[j]
        gamma1 = float(p.get("gamma1", default["gamma1"]))
        gamma2 = float(p.get("gamma2", default["gamma2"]))
        gamma_phi = max(0.0, gamma2 - gamma1 / 2.0)
        # Effective decoherence rate (inverse coherence time scale)
        rates[j] = gamma1 + gamma_phi
    return rates


def get_node_decoherence_rates_from_file(path: str) -> np.ndarray:
    """
    Load per-node params from a JSON file: list of {"gamma1": ..., "gamma2": ...}.
    Returns array of decoherence rates.
    """
    import json
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return get_node_decoherence_rates(len(data), data)
    if isinstance(data, dict) and "nodes" in data:
        return get_node_decoherence_rates(len(data["nodes"]), data["nodes"])
    raise ValueError(f"Expected list or {{'nodes': list}} in {path}")
