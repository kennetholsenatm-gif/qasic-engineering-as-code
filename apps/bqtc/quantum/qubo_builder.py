"""
Build a QuadraticProgram (QUBO) from the expected bandwidth matrix.
Decision: which path each VNI uses (one path per VNI). Objective: minimize congestion
(e.g. sum over paths of (load/capacity)^2 to balance utilization).
"""

from typing import List, Tuple

import numpy as np

try:
    from qiskit_optimization import QuadraticProgram
except ImportError:
    QuadraticProgram = None  # type: ignore


def bandwidth_matrix_to_qubo(
    bandwidth_matrix: np.ndarray,
    path_capacities: List[float],
    vnis: List[int],
    path_ids: List[str],
) -> Tuple["QuadraticProgram", List[Tuple[int, str]]]:
    """
    bandwidth_matrix: B[vni_idx][path_idx] in bytes/sec
    path_capacities: capacity per path in bytes/sec (same order as path_ids)
    Returns (QuadraticProgram, list of (vni, path_id) in variable order).
    """
    if QuadraticProgram is None:
        raise ImportError("qiskit_optimization is required. pip install qiskit-optimization")
    n_vni, n_path = bandwidth_matrix.shape
    # Ensure capacities are positive
    caps = np.array(path_capacities, dtype=np.float64)
    if caps.size != n_path:
        caps = np.ones(n_path) * (1e9 if path_capacities else 1e9)
    caps = np.maximum(caps * 1e6 / 8.0, 1.0)  # Mbps -> bytes/sec, avoid zero

    qp = QuadraticProgram("path_selection")
    # Binary x[vni, path]: 1 if VNI v uses path p
    var_order: List[Tuple[int, str]] = []
    for vni_idx in range(n_vni):
        for path_idx in range(n_path):
            name = f"x_{vni_idx}_{path_idx}"
            qp.binary_var(name=name)
            vni = vnis[vni_idx] if vni_idx < len(vnis) else vni_idx
            pid = path_ids[path_idx] if path_idx < len(path_ids) else f"path{path_idx}"
            var_order.append((vni, pid))

    # Constraint: each VNI uses exactly one path
    for vni_idx in range(n_vni):
        linear = {f"x_{vni_idx}_{p}": 1.0 for p in range(n_path)}
        qp.linear_constraint(linear=linear, sense="==", rhs=1.0, name=f"one_path_vni{vni_idx}")

    # Objective: minimize sum_p (load_p / cap_p)^2
    # load_p = sum_v B[v,p] * x[v,p]  =>  (load_p)^2 = sum_v B^2 x_v^2 + 2 sum_{v<w} B_v B_w x_v x_w
    # For binary x, x^2 = x. So linear term B^2/cap^2 * x, quadratic 2 B_v B_w/cap^2 * x_v x_w
    scale = 1.0 / (caps ** 2)
    linear: dict = {}
    quadratic: dict = {}
    for p in range(n_path):
        for v in range(n_vni):
            name_v = f"x_{v}_{p}"
            b_v = bandwidth_matrix[v, p]
            linear[name_v] = linear.get(name_v, 0) + (b_v ** 2) * scale[p]
        for v1 in range(n_vni):
            for v2 in range(n_vni):
                if v1 < v2:
                    name1, name2 = f"x_{v1}_{p}", f"x_{v2}_{p}"
                    b1, b2 = bandwidth_matrix[v1, p], bandwidth_matrix[v2, p]
                    key = (name1, name2)
                    quadratic[key] = quadratic.get(key, 0) + 2.0 * b1 * b2 * scale[p]

    qp.minimize(linear=linear, quadratic=quadratic)
    return qp, var_order
