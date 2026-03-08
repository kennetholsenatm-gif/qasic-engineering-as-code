"""Tests for engineering.routing_qubo_qaoa: build_routing_qubo, interpret_routing, solve_routing (budget)."""
from __future__ import annotations

import numpy as np
import pytest

# interpret_routing only needs numpy; build_routing_qubo needs qiskit_optimization
from src.core_compute.engineering.routing_qubo_qaoa import interpret_routing

try:
    from qiskit_optimization import QuadraticProgram
    from src.core_compute.engineering.routing_qubo_qaoa import build_routing_qubo, solve_routing
    HAS_QISKIT_OPT = True
except ImportError:
    HAS_QISKIT_OPT = False
    solve_routing = None


def test_interpret_routing_identity():
    # Solution: logical i at physical i -> x_0_0=1, x_1_1=1, x_2_2=1
    n_logical, n_physical = 3, 3
    x = np.zeros(n_logical * n_physical)
    x[0 * 3 + 0] = 1
    x[1 * 3 + 1] = 1
    x[2 * 3 + 2] = 1
    mapping = interpret_routing(x, n_logical, n_physical)
    assert mapping == [(0, 0), (1, 1), (2, 2)]


def test_interpret_routing_permutation():
    # Logical 0 -> physical 2, logical 1 -> 0, logical 2 -> 1
    n_logical, n_physical = 3, 3
    x = np.zeros(n_logical * n_physical)
    x[0 * 3 + 2] = 1
    x[1 * 3 + 0] = 1
    x[2 * 3 + 1] = 1
    mapping = interpret_routing(x, n_logical, n_physical)
    assert mapping == [(0, 2), (1, 0), (2, 1)]


@pytest.mark.skipif(not HAS_QISKIT_OPT, reason="qiskit_optimization not installed")
def test_build_routing_qubo():
    qp = build_routing_qubo(num_logical_qubits=3, num_physical_nodes=3)
    assert qp is not None
    assert qp.get_num_binary_vars() == 9
    assert qp.get_num_linear_constraints() == 6  # 3 + 3


@pytest.mark.skipif(not HAS_QISKIT_OPT or solve_routing is None, reason="qiskit_optimization not installed")
def test_solve_routing_with_budget_preset():
    """solve_routing with small maxiter/reps (budget preset) returns a valid result."""
    qp = build_routing_qubo(num_logical_qubits=3, num_physical_nodes=3)
    result = solve_routing(
        qp, use_qaoa=True, qaoa_reps=1, optimizer_maxiter=20
    )
    assert "x" in result and "fval" in result and "solver" in result
    assert result["solver"] in ("QAOA", "QAOA (real hardware)", "NumPyMinimumEigensolver", "NumPyMinimumEigensolver (fallback)")
    assert result["x"] is not None
    assert result["fval"] is None or isinstance(result["fval"], (int, float))
