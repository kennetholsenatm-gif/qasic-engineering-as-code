"""
Quantum Processing component.

Given a bandwidth matrix and topology, solve for an optimal path
assignment and drive the VyOS actuator to apply BGP local-preference.
"""

from typing import Any, Dict, List

import numpy as np

from quantum.solver import solve_path_distribution
from quantum.mapping import path_distribution_to_bgp_preferences
from actuator.apply import apply_directives


def optimize_paths(
    bandwidth_matrix: np.ndarray,
    path_capacities: List[float],
    vnis: List[int],
    path_ids: List[str],
    quantum_cfg: Dict[str, Any],
) -> Dict[int, str]:
    """
    Run the Qiskit optimizer and return vni -> preferred path_id.
    """
    vni_to_path, _ = solve_path_distribution(
        bandwidth_matrix,
        path_capacities,
        vnis=vnis,
        path_ids=path_ids,
        qaoa_reps=quantum_cfg.get("qaoa_reps", 2),
        use_simulator=quantum_cfg.get("use_simulator", True),
    )
    return vni_to_path


def build_directives(
    vni_to_path: Dict[int, str],
    path_ids: List[str],
    leafs: List[dict],
) -> List[dict]:
    """
    Convert path assignments into BGP local-preference directives.
    """
    return path_distribution_to_bgp_preferences(
        vni_to_path,
        path_ids,
        leafs,
    )


def apply_decisions(
    directives: List[dict],
    leafs: List[dict],
    actuator_cfg: Dict[str, Any],
) -> List[dict]:
    """
    Apply directives to VyOS leafs using the actuator layer.
    """
    return apply_directives(
        directives,
        leafs,
        dry_run=actuator_cfg.get("dry_run", True),
        rate_limit_seconds=float(actuator_cfg.get("rate_limit_seconds", 5)),
    )

