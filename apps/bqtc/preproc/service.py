"""
Quantum Pre-processing component.

Uses Bayesian inference to produce the expected bandwidth matrix
and builds the corresponding QUBO for the quantum optimizer.
"""

from typing import Any, Dict, List, Tuple

import numpy as np

from bayesian.inference import run_inference
from quantum.qubo_builder import bandwidth_matrix_to_qubo


def compute_bandwidth_matrix(
    buffer: Any,
    vnis: List[int],
    path_ids: List[str],
    bayesian_cfg: Dict[str, Any],
) -> np.ndarray:
    """
    Run the Bayesian inference engine and return B[vni][path] in bytes/sec.
    """
    return run_inference(
        buffer,
        vnis=vnis,
        path_ids=path_ids,
        backend=bayesian_cfg.get("backend", "sklearn"),
        model_type=bayesian_cfg.get("model_type", "bayesian_ridge"),
    )


def build_qubo(
    bandwidth_matrix: np.ndarray,
    path_capacities: List[float],
    vnis: List[int],
    path_ids: List[str],
):
    """
    Build a QuadraticProgram QUBO from the bandwidth matrix.
    Returns (QuadraticProgram, variable_order).
    """
    return bandwidth_matrix_to_qubo(
        bandwidth_matrix,
        path_capacities,
        vnis,
        path_ids,
    )

