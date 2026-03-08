"""
Run Qiskit QAOA / MinimumEigenOptimizer to solve the path-selection QUBO.
Returns the optimal path distribution (which path per VNI).
"""

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    from qiskit.primitives import StatevectorSampler
    from qiskit_optimization import QuadraticProgram
    from qiskit_optimization.algorithms import MinimumEigenOptimizer
    from qiskit_optimization.minimum_eigensolvers import QAOA
    from qiskit_optimization.optimizers import COBYLA
    from qiskit_optimization.utils import algorithm_globals
    QISKIT_OPT_AVAILABLE = True
except ImportError:
    QISKIT_OPT_AVAILABLE = False

from .qubo_builder import bandwidth_matrix_to_qubo


def solve_path_distribution(
    bandwidth_matrix: np.ndarray,
    path_capacities: List[float],
    vnis: List[int],
    path_ids: List[str],
    qaoa_reps: int = 2,
    use_simulator: bool = True,
    seed: Optional[int] = None,
) -> Tuple[Dict[int, str], Any]:
    """
    Solve QUBO for path selection. Returns (vni -> path_id, optimization result).
    """
    if not QISKIT_OPT_AVAILABLE:
        raise ImportError("qiskit_optimization and qiskit are required.")
    qp, var_order = bandwidth_matrix_to_qubo(
        bandwidth_matrix, path_capacities, vnis, path_ids
    )
    if seed is not None:
        algorithm_globals.random_seed = seed
    sampler = StatevectorSampler(seed=seed or 42)
    # QAOA uses 2*reps parameters (gamma and beta per layer)
    initial_point = [1.0] * (2 * max(1, qaoa_reps))
    try:
        qaoa_mes = QAOA(
            sampler=sampler,
            optimizer=COBYLA(),
            initial_point=initial_point,
            reps=qaoa_reps,
        )
    except TypeError:
        qaoa_mes = QAOA(
            sampler=sampler,
            optimizer=COBYLA(),
            initial_point=initial_point[:2],
        )
    optimizer = MinimumEigenOptimizer(qaoa_mes)
    result = optimizer.solve(qp)
    # Map solution back to vni -> path_id (one path per VNI)
    vni_to_path: Dict[int, str] = {}
    n_path = len(path_ids)
    if result.x is not None:
        for vni_idx, vni in enumerate(vnis):
            for path_idx in range(n_path):
                idx = vni_idx * n_path + path_idx
                if idx < len(result.x) and result.x[idx] >= 0.5:
                    vni_to_path[vni] = path_ids[path_idx]
                    break
    return vni_to_path, result
