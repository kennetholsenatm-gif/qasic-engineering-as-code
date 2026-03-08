"""
Metasurface qubit routing via QUBO: map logical qubits (e.g. Alice, Bob, Message)
to physical nodes (metasurface interaction zones) to minimize interaction penalty/distance.
Uses Qiskit 2.x + qiskit-optimization 0.7: QAOA with StatevectorSampler (simulation) or
IBM Runtime SamplerV2 (real hardware). Classical fallback via NumPyMinimumEigensolver.

Ref: Holographic Metasurfaces and Cryogenic Architectures for Scalable Quantum Computing
     and Satellite Communications.

API (qiskit-optimization 0.7 / Qiskit 2.x):
  - QuadraticProgram, MinimumEigenOptimizer, QAOA, NumPyMinimumEigensolver, COBYLA
  - Simulation: qiskit.primitives.StatevectorSampler
  - Real hardware: qiskit_ibm_runtime.SamplerV2 + Session + pass_manager
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
import numpy as np

# qiskit-optimization 0.7 (Qiskit 2.x) — import in steps to tolerate partial failures (e.g. Python 3.14)
_qiskit_opt_import_error = None
HAS_QISKIT_OPT = False
QuadraticProgram = None
MinimumEigenOptimizer = None
QAOA = None
NumPyMinimumEigensolver = None
COBYLA = None

try:
    from qiskit_optimization import QuadraticProgram
    from qiskit_optimization.algorithms import MinimumEigenOptimizer
    from qiskit_optimization.optimizers import COBYLA
except ImportError as e:
    _qiskit_opt_import_error = e
else:
    try:
        from qiskit_optimization.minimum_eigensolvers import QAOA, NumPyMinimumEigensolver
    except ImportError as e:
        _qiskit_opt_import_error = e
        QAOA = None
        NumPyMinimumEigensolver = None
    HAS_QISKIT_OPT = (
        QuadraticProgram is not None
        and MinimumEigenOptimizer is not None
        and (QAOA is not None or NumPyMinimumEigensolver is not None)
    )

# Qiskit 2.x primitives: StatevectorSampler (exact) preferred for simulation
try:
    from qiskit.primitives import StatevectorSampler
    QAOA_SAMPLER = StatevectorSampler(seed=42)
    HAS_QAOA = HAS_QISKIT_OPT and QAOA is not None
except ImportError:
    try:
        from qiskit.primitives import Sampler
        QAOA_SAMPLER = Sampler()
        HAS_QAOA = HAS_QISKIT_OPT and QAOA is not None
    except ImportError:
        QAOA_SAMPLER = None
        HAS_QAOA = False

# Classical fallback: exact solve via NumPyMinimumEigensolver (no CobylaOptimizer needed)
HAS_CLASSICAL = HAS_QISKIT_OPT and NumPyMinimumEigensolver is not None


# API pattern aligned with BQTC/QRNG: env IBM_QUANTUM_TOKEN, channel="ibm_quantum_platform"
IBM_QUANTUM_TOKEN_ENV = "IBM_QUANTUM_TOKEN"
IBM_CHANNEL = "ibm_quantum_platform"


def get_hardware_sampler_and_pass_manager(backend_name: str | None = None, ibm_token: str | None = None):
    """
    Get (sampler, pass_manager, backend) for real IBM hardware using qiskit-ibm-runtime.
    Uses the same API pattern as BQTC QRNG: token from env IBM_QUANTUM_TOKEN or passed in,
    channel="ibm_quantum_platform", SamplerV2(backend).
    Returns (sampler, pass_manager, backend) or (None, None, None).
    """
    try:
        from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
        from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
    except ImportError as e:
        print(f"  Real hardware requires qiskit-ibm-runtime: {e}")
        return None, None, None

    token = ibm_token or os.environ.get(IBM_QUANTUM_TOKEN_ENV)
    if not token:
        print(f"  No IBM Quantum token. Set env {IBM_QUANTUM_TOKEN_ENV} or pass ibm_token=.")
        print("  Get a token at https://quantum.ibm.com/")
        return None, None, None

    try:
        service = QiskitRuntimeService(channel=IBM_CHANNEL, token=token)
        if backend_name:
            backend = service.backend(backend_name)
        else:
            backend = service.least_busy(simulator=False, operational=True)
        if backend is None:
            print("  No operational real backend found.")
            return None, None, None
        pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
        sampler = SamplerV2(backend)
        return sampler, pm, backend
    except Exception as e:
        print(f"  Failed to connect to IBM Quantum: {e}")
        print(f"  Set env {IBM_QUANTUM_TOKEN_ENV} or use QiskitRuntimeService.save_account(channel={IBM_CHANNEL!r}, token='...')")
        return None, None, None


def build_routing_qubo(
    num_logical_qubits: int = 3,
    num_physical_nodes: int | None = None,
    interaction_matrix: np.ndarray | None = None,
    distance_penalty_scale: float = 1.0,
    node_decoherence_rates: np.ndarray | None = None,
    decoherence_penalty_scale: float = 1.0,
) -> QuadraticProgram:
    """
    Build QUBO for mapping logical qubits to physical nodes.
    - Each logical qubit maps to exactly one physical node (and vice versa).
    - Objective: minimize sum over (i1,i2) that need to interact of
      distance_penalty(j1,j2) * x_{i1,j1}*x_{i2,j2}, plus optional linear terms
      decoherence_penalty_scale * node_decoherence_rates[j] * x_{i,j} to penalize
      assigning qubits to high-decoherence nodes.
    If interaction_matrix is None, assume all pairs (i1,i2) need to interact (e.g. linear chain).
    """
    num_physical_nodes = num_physical_nodes or num_logical_qubits
    qp = QuadraticProgram(name="Metasurface_Qubit_Routing")

    # Binary variables x_{i,j} = 1 iff logical qubit i is at physical node j
    for i in range(num_logical_qubits):
        for j in range(num_physical_nodes):
            qp.binary_var(name=f"x_{i}_{j}")

    # Each logical qubit assigned to exactly one physical node
    for i in range(num_logical_qubits):
        qp.linear_constraint(
            linear={f"x_{i}_{j}": 1 for j in range(num_physical_nodes)},
            sense="==",
            rhs=1,
            name=f"log_req_{i}",
        )

    # Each physical node gets exactly one logical qubit
    for j in range(num_physical_nodes):
        qp.linear_constraint(
            linear={f"x_{i}_{j}": 1 for i in range(num_logical_qubits)},
            sense="==",
            rhs=1,
            name=f"phys_req_{j}",
        )

    # Interaction penalty: for each pair (i1,i2) that must interact, penalize distance between their nodes
    if interaction_matrix is None:
        # Default: linear chain (0-1, 1-2) -> interactions (0,1) and (1,2)
        interaction_matrix = np.zeros((num_logical_qubits, num_logical_qubits))
        for i in range(num_logical_qubits - 1):
            interaction_matrix[i, i + 1] = 1
            interaction_matrix[i + 1, i] = 1

    quadratic = {}
    for i1 in range(num_logical_qubits):
        for i2 in range(num_logical_qubits):
            if i1 != i2 and interaction_matrix[i1, i2] != 0:
                for j1 in range(num_physical_nodes):
                    for j2 in range(num_physical_nodes):
                        if j1 != j2:
                            dist = abs(j1 - j2)
                            key = (f"x_{i1}_{j1}", f"x_{i2}_{j2}")
                            quadratic[key] = distance_penalty_scale * dist

    # Optional: linear decoherence penalty per (i, j)
    linear = {}
    if node_decoherence_rates is not None and len(node_decoherence_rates) >= num_physical_nodes:
        for i in range(num_logical_qubits):
            for j in range(num_physical_nodes):
                linear[f"x_{i}_{j}"] = decoherence_penalty_scale * float(node_decoherence_rates[j])

    if linear:
        qp.minimize(linear=linear, quadratic=quadratic)
    else:
        qp.minimize(quadratic=quadratic)
    return qp


def solve_routing(
    qp: QuadraticProgram,
    use_qaoa: bool = True,
    qaoa_reps: int = 2,
    optimizer_maxiter: int = 100,
    sampler=None,
    pass_manager=None,
) -> dict:
    """Solve routing QUBO. Returns dict with x (solution), fval, and solver name.
    If sampler is provided (e.g. IBM SamplerV2), use it for QAOA; pass_manager is required for V2 samplers.
    """
    effective_sampler = sampler if sampler is not None else QAOA_SAMPLER
    if use_qaoa and HAS_QISKIT_OPT and QAOA is not None and COBYLA is not None and effective_sampler is not None:
        try:
            initial_point = [1.0] * (2 * qaoa_reps)
            qaoa_kw = dict(
                sampler=effective_sampler,
                optimizer=COBYLA(maxiter=optimizer_maxiter),
                reps=qaoa_reps,
                initial_point=initial_point,
            )
            if pass_manager is not None:
                qaoa_kw["pass_manager"] = pass_manager
            qaoa_mes = QAOA(**qaoa_kw)
            opt = MinimumEigenOptimizer(qaoa_mes)
            result = opt.solve(qp)
            return {
                "x": result.x,
                "fval": result.fval,
                "solver": "QAOA (real hardware)" if pass_manager is not None else "QAOA",
            }
        except Exception as e:
            if HAS_CLASSICAL:
                exact_mes = NumPyMinimumEigensolver()
                opt = MinimumEigenOptimizer(exact_mes)
                result = opt.solve(qp)
                return {
                    "x": result.x,
                    "fval": result.fval,
                    "solver": "NumPyMinimumEigensolver (fallback)",
                    "qaoa_error": str(e),
                }
            raise RuntimeError(f"QAOA failed and no classical fallback: {e}") from e

    if HAS_CLASSICAL and HAS_QISKIT_OPT:
        exact_mes = NumPyMinimumEigensolver()
        opt = MinimumEigenOptimizer(exact_mes)
        result = opt.solve(qp)
        return {"x": result.x, "fval": result.fval, "solver": "NumPyMinimumEigensolver"}
    raise RuntimeError(
        "Install qiskit and qiskit-optimization (e.g. pip install qiskit qiskit-optimization)."
    )


def estimate_quantum_resources(
    num_logical_qubits: int = 3,
    num_physical_nodes: int | None = None,
    qaoa_reps: int = 2,
    optimizer_maxiter: int = 100,
    shots_per_eval: int = 1024,
) -> dict:
    """
    Rough estimate of quantum computation used by the routing QAOA.
    Returns dict with qubits, circuit evaluations, total shots, and rough time estimates.
    """
    n_phys = num_physical_nodes or num_logical_qubits
    n_vars = num_logical_qubits * n_phys
    n_qubits = n_vars
    # COBYLA typically uses ~1 cost evaluation per iteration (plus line-search steps)
    n_circuit_evals = optimizer_maxiter  # order of magnitude
    total_shots = n_circuit_evals * shots_per_eval

    # QAOA circuit: 2 layers (reps=2) of cost + mixer. Cost has O(n_vars^2) two-qubit terms in worst case.
    # Rough gate count per layer: cost ~ O(quadratic terms in QUBO), mixer = n_qubits X gates.
    depth_per_layer_2q = min(n_vars * (n_vars - 1) // 2, 50)  # cap for sparse QUBO
    approx_2q_gates_per_circuit = 2 * qaoa_reps * (depth_per_layer_2q + n_qubits)

    # Time estimates (order of magnitude)
    # Simulator (StatevectorSampler): no shots, exact; 1 "eval" per iteration
    sim_evals = n_circuit_evals
    sim_time_sec = sim_evals * 0.01 * (2 ** min(n_qubits, 12)) / 1e6  # rough: scale with 2^n
    if n_qubits <= 10:
        sim_time_sec = max(0.5, sim_evals * 0.05)  # ~50 ms per eval for small n
    # Real hardware: shots matter
    us_per_shot = 50  # ~20–50 us per shot (gates + readout) on superconducting
    hw_execution_sec = total_shots * us_per_shot / 1e6
    hw_queue_note = "Queue on shared cloud devices often dominates (minutes to hours)."

    return {
        "n_qubits": n_qubits,
        "n_binary_vars": n_vars,
        "qaoa_reps": qaoa_reps,
        "optimizer_maxiter": optimizer_maxiter,
        "circuit_evaluations": n_circuit_evals,
        "shots_per_evaluation": shots_per_eval,
        "total_shots_on_hardware": total_shots,
        "approx_2q_gates_per_circuit": approx_2q_gates_per_circuit,
        "simulator_time_sec_rough": round(sim_time_sec, 1),
        "hardware_execution_sec_rough": round(hw_execution_sec, 1),
        "hardware_note": hw_queue_note,
    }


def interpret_routing(
    x: list[float] | np.ndarray,
    num_logical: int,
    num_physical: int,
) -> list[tuple[int, int]]:
    """Map solution vector (variable order: x_0_0, x_0_1, ..., x_{L-1}_{P-1}) to (logical, physical)."""
    arr = np.asarray(x).ravel()
    mapping = []
    for i in range(num_logical):
        for j in range(num_physical):
            if arr[i * num_physical + j] > 0.5:
                mapping.append((i, j))
                break
    return mapping


def main() -> None:
    parser = argparse.ArgumentParser(description="Metasurface QUBO routing (QAOA or classical)")
    parser.add_argument(
        "--hardware",
        action="store_true",
        help="Run QAOA on real IBM Quantum hardware (requires qiskit-ibm-runtime and saved credentials)",
    )
    parser.add_argument(
        "--backend",
        type=str,
        default=None,
        help="IBM backend name (default: least_busy). Ignored unless --hardware.",
    )
    parser.add_argument(
        "--token",
        type=str,
        default=None,
        help=f"IBM Quantum API token (default: env {IBM_QUANTUM_TOKEN_ENV}). Ignored unless --hardware.",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        metavar="FILE",
        help="Write result (mapping, solver, objective, backend) to JSON file (e.g. -o routing_result.json).",
    )
    parser.add_argument(
        "--maxiter",
        type=int,
        default=100,
        metavar="N",
        help="COBYLA max iterations (default 100). Use lower for faster/cheaper hardware runs.",
    )
    parser.add_argument(
        "--reps",
        type=int,
        default=2,
        metavar="N",
        help="QAOA layers (default 2). Use 1 with --fast for cheaper runs.",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Budget preset: --maxiter 20 --reps 1 for affordable runs under 5 min QPU time.",
    )
    parser.add_argument(
        "--topology",
        "-t",
        type=str,
        default="linear_chain",
        choices=["linear", "linear_chain", "star", "repeater", "repeater_chain"],
        help="Named logical topology (default: linear_chain).",
    )
    parser.add_argument(
        "--qubits",
        "-n",
        type=int,
        default=3,
        metavar="N",
        help="Number of logical qubits (default: 3).",
    )
    parser.add_argument(
        "--hub",
        type=int,
        default=0,
        help="Hub node index for star topology (default: 0).",
    )
    parser.add_argument(
        "--use-qutip-decoherence",
        action="store_true",
        help="Use QuTiP-based per-node decoherence rates in QUBO (default gamma1/gamma2 per node).",
    )
    parser.add_argument(
        "--decoherence-file",
        type=str,
        default=None,
        metavar="FILE",
        help="JSON file with per-node gamma1/gamma2 (or 'nodes' list); implies decoherence-aware routing.",
    )
    parser.add_argument(
        "--decoherence-penalty-scale",
        type=float,
        default=1.0,
        help="Scale factor for decoherence linear terms in QUBO (default: 1.0).",
    )
    args = parser.parse_args()

    # Apply --fast preset
    maxiter = 20 if args.fast else args.maxiter
    reps = 1 if args.fast else args.reps

    num_logical = args.qubits
    num_physical = num_logical  # Same number of physical nodes

    # Resolve topology and interaction matrix for QUBO
    interaction_matrix = None
    try:
        from pathlib import Path
        _root = Path(__file__).resolve().parents[1]
        if str(_root) not in sys.path:
            sys.path.insert(0, str(_root))
        from src.core_compute.asic.topology_builder import get_topology
        kw = {"hub": args.hub} if args.topology == "star" else {}
        _topo, interaction_matrix = get_topology(args.topology, num_logical, **kw)
    except ImportError:
        pass  # Use default linear chain interaction_matrix in build_routing_qubo
    except Exception as e:
        print(f"  Topology error: {e}", file=sys.stderr)
        sys.exit(1)

    if not HAS_QISKIT_OPT:
        print("qiskit_optimization not available.", file=sys.stderr)
        if _qiskit_opt_import_error is not None:
            print(f"  Import error: {_qiskit_opt_import_error}", file=sys.stderr)
        print("  Install with: python -m pip install qiskit qiskit-optimization hashable-list ordered-set", file=sys.stderr)
        print("  (Use the same 'python' you run this script with. Check: python -c \"import sys; print(sys.executable)\")", file=sys.stderr)
        sys.exit(1)

    node_decoherence_rates = None
    if args.decoherence_file:
        try:
            from engineering.decoherence_rates import get_node_decoherence_rates_from_file
            node_decoherence_rates = get_node_decoherence_rates_from_file(args.decoherence_file)
            print(f"  Decoherence rates loaded from {args.decoherence_file} (length {len(node_decoherence_rates)})")
        except Exception as e:
            try:
                from decoherence_rates import get_node_decoherence_rates_from_file
                node_decoherence_rates = get_node_decoherence_rates_from_file(args.decoherence_file)
                print(f"  Decoherence rates loaded from {args.decoherence_file} (length {len(node_decoherence_rates)})")
            except Exception as e2:
                print(f"  Warning: could not load decoherence file: {e2}", file=sys.stderr)
    elif args.use_qutip_decoherence:
        try:
            from engineering.decoherence_rates import get_node_decoherence_rates
            node_decoherence_rates = get_node_decoherence_rates(num_physical)
            print("  Using QuTiP-based default decoherence rates per node")
        except Exception as e:
            try:
                from decoherence_rates import get_node_decoherence_rates
                node_decoherence_rates = get_node_decoherence_rates(num_physical)
                print("  Using QuTiP-based default decoherence rates per node")
            except Exception as e2:
                print(f"  Warning: could not compute decoherence rates: {e2}", file=sys.stderr)

    qp = build_routing_qubo(
        num_logical_qubits=num_logical,
        num_physical_nodes=num_physical,
        interaction_matrix=interaction_matrix,
        node_decoherence_rates=node_decoherence_rates,
        decoherence_penalty_scale=args.decoherence_penalty_scale,
    )
    print("Metasurface Qubit Routing QUBO (minimize interaction distance" +
          (", decoherence penalty" if node_decoherence_rates is not None else "") + ")")
    print(f"  Topology: {args.topology}, Logical qubits: {num_logical}, Physical nodes: {num_physical}")

    use_qaoa = HAS_QAOA or args.hardware
    if not use_qaoa:
        print("  QAOA not available; using classical NumPyMinimumEigensolver.")

    backend_name_for_output = None
    if args.hardware:
        sampler, pm, backend = get_hardware_sampler_and_pass_manager(
            args.backend, ibm_token=args.token
        )
        if sampler is None or pm is None:
            print("  Falling back to simulation.")
            result = solve_routing(qp, use_qaoa=HAS_QAOA, qaoa_reps=reps, optimizer_maxiter=maxiter)
        else:
            backend_name_for_output = backend.name
            print(f"  Using real backend: {backend_name_for_output}")
            est = estimate_quantum_resources(
                num_logical_qubits=num_logical,
                num_physical_nodes=num_physical,
                qaoa_reps=reps,
                optimizer_maxiter=maxiter,
            )
            qpu_sec = est["total_shots_on_hardware"] * 50e-6
            print(f"  [Est. QPU time ~{qpu_sec:.1f} s (~{est['total_shots_on_hardware']} shots)]")
            if args.fast:
                print("  (--fast: budget preset for affordable runs under 5 min QPU time.)")
            result = solve_routing(
                qp, use_qaoa=True, qaoa_reps=reps, optimizer_maxiter=maxiter,
                sampler=sampler, pass_manager=pm
            )
    else:
        # Optional: print rough quantum resource estimate when using QAOA
        if use_qaoa and HAS_QAOA:
            est = estimate_quantum_resources(
                num_logical_qubits=num_logical,
                num_physical_nodes=num_physical,
                qaoa_reps=reps,
                optimizer_maxiter=maxiter,
            )
            qpu_sec = est["total_shots_on_hardware"] * 50e-6  # ~50 us per shot
            print(f"  [QAOA resource estimate: {est['n_qubits']} qubits, ~{est['circuit_evaluations']} circuit evals, "
                  f"simulator ~{est['simulator_time_sec_rough']} s; on real HW ~{est['total_shots_on_hardware']} shots, "
                  f"est. QPU time ~{qpu_sec:.1f} s]")
            if args.fast:
                print("  (--fast: budget preset for affordable runs under 5 min QPU time.)")
        result = solve_routing(qp, use_qaoa=use_qaoa, qaoa_reps=reps, optimizer_maxiter=maxiter)

    print(f"  Solver: {result['solver']}, objective value: {result['fval']}")

    x_vals = result["x"]
    mapping = None
    if x_vals is None:
        print("  Warning: no solution (result.x is None). Check optimizer status.")
    else:
        x_vals = np.asarray(x_vals).ravel()
        mapping = interpret_routing(x_vals, num_logical, num_physical)
        print(f"  Optimal mapping (logical -> physical): {mapping}")
        print("  (Interpretation: which logical qubit sits on which metasurface zone.)")

    if args.output:
        out = {
            "num_logical_qubits": num_logical,
            "num_physical_nodes": num_physical,
            "topology": args.topology,
            "solver": result["solver"],
            "objective_value": float(result["fval"]) if result["fval"] is not None else None,
            "backend": backend_name_for_output,
            "mapping": [{"logical": a, "physical": b} for a, b in (mapping or [])],
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(out, f, indent=2)
        except OSError as e:
            print(f"  Error writing output: {e}", file=sys.stderr)
            sys.exit(1)
        print(f"  Result written to {args.output}")

    sys.exit(0)


if __name__ == "__main__":
    main()
