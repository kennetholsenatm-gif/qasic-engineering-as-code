"""
Run an ASIC protocol (teleportation, Bell, commitment, thief) on IBM Quantum or simulator.
Builds a Qiskit QuantumCircuit from asic.circuit Op list and runs a single Sampler job.
Use for demos and validation; single job keeps cost under 5 minutes QPU time.

Usage (from repo root):
  python engineering/run_protocol_on_ibm.py                    # sim, teleport
  python engineering/run_protocol_on_ibm.py --protocol bell   # Bell pair
  python engineering/run_protocol_on_ibm.py --hardware        # real IBM backend
  python engineering/run_protocol_on_ibm.py -o result.json    # write JSON
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

# Run from repo root so asic is importable
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from src.core_compute.asic.circuit import Op, protocol_teleport_ops, protocol_commitment_ops, protocol_thief_ops

IBM_QUANTUM_TOKEN_ENV = "IBM_QUANTUM_TOKEN"
IBM_CHANNEL = "ibm_quantum_platform"


def bell_ops() -> list[Op]:
    """Bell pair on qubits 0,1: H(0), CNOT(0,1)."""
    return [Op("H", [0]), Op("CNOT", [0, 1])]


def asic_ops_to_qiskit_circuit(ops: list[Op], num_qubits: int | None = None) -> "QuantumCircuit":
    """Build a Qiskit QuantumCircuit from a list of ASIC Op. Adds measurement on all qubits."""
    from qiskit import QuantumCircuit

    if not ops:
        n = num_qubits or 1
        qc = QuantumCircuit(n)
        qc.measure_all()
        return qc

    max_q = max(max(op.targets) for op in ops)
    n = num_qubits if num_qubits is not None else max_q + 1
    qc = QuantumCircuit(n)

    for op in ops:
        gate = op.gate.upper()
        t = op.targets
        if gate == "H":
            qc.h(t[0])
        elif gate == "X":
            qc.x(t[0])
        elif gate == "Z":
            qc.z(t[0])
        elif gate == "RX":
            angle = op.param if op.param is not None else 0.0
            qc.rx(float(angle), t[0])
        elif gate == "CNOT":
            qc.cx(t[0], t[1])
        else:
            raise ValueError(f"Unsupported gate for Qiskit: {op.gate}")

    qc.measure_all()
    return qc


def get_protocol_ops(protocol: str) -> list[Op]:
    """Return the op list for the given protocol name."""
    if protocol == "teleport":
        return protocol_teleport_ops()
    if protocol == "bell":
        return bell_ops()
    if protocol == "commitment":
        return protocol_commitment_ops()
    if protocol == "thief":
        return protocol_thief_ops()
    raise ValueError(f"Unknown protocol: {protocol}. Use teleport|bell|commitment|thief.")


def _extract_counts(pub_result) -> dict:
    """Extract measurement counts from a Sampler pub result (V1 or V2 style)."""
    data = getattr(pub_result, "data", pub_result)
    if hasattr(data, "meas") and hasattr(data.meas, "get_counts"):
        return dict(data.meas.get_counts())
    if hasattr(data, "get_counts"):
        return dict(data.get_counts())
    if hasattr(data, "counts"):
        return dict(data.counts) if data.counts else {}
    return dict(getattr(data, "counts", {}) or {})


def submit_protocol_job_via_circuit_function(
    protocol: str,
    backend_name: str | None = None,
    shots: int = 1024,
    ibm_token: str | None = None,
    circuit_function_id: str | None = None,
) -> tuple[str, object, str | None]:
    """
    Submit protocol circuit via Qiskit Functions Catalog (circuit function) when available.
    Returns (job_id, job, backend_name). Use when use_circuit_function=True for error
    mitigation and resource_usage. Raises ImportError if qiskit-ibm-catalog not installed,
    or RuntimeError on submission failure (caller should fall back to submit_protocol_job).
    """
    import uuid
    try:
        from qiskit_ibm_catalog import QiskitFunctionsCatalog
    except ImportError as e:
        raise ImportError("qiskit-ibm-catalog required for circuit function; pip install qiskit-ibm-catalog") from e
    token = ibm_token or os.environ.get(IBM_QUANTUM_TOKEN_ENV)
    if not token:
        raise RuntimeError("IBM token required for Qiskit Functions")
    func_id = circuit_function_id or os.environ.get("QISKIT_CIRCUIT_FUNCTION_ID", "ibm/circuit-function")
    ops = get_protocol_ops(protocol)
    qc = asic_ops_to_qiskit_circuit(ops)
    catalog = QiskitFunctionsCatalog(channel="ibm_quantum_platform", token=token)
    circuit_fn = catalog.load(func_id)
    backend_str = backend_name or "ibm_pittsburgh"
    job = circuit_fn.run(circuit=qc, backend_name=backend_str, shots=shots)
    job_id = str(uuid.uuid4())
    return job_id, job, backend_str


def submit_protocol_job(
    protocol: str,
    backend_name: str | None = None,
    shots: int = 1024,
    ibm_token: str | None = None,
) -> tuple[str, object, str | None]:
    """
    Submit protocol job to IBM hardware without waiting. Returns (job_id, job, backend_name).
    job_id is a string; job has .status() and .result() for async polling.
    """
    import uuid
    ops = get_protocol_ops(protocol)
    qc = asic_ops_to_qiskit_circuit(ops)
    sampler, _pm, backend = get_hardware_sampler_and_pass_manager(backend_name, ibm_token=ibm_token)
    if sampler is None or backend is None:
        raise RuntimeError("IBM hardware not available (token or backend)")
    from qiskit import transpile
    qc_transpiled = transpile(qc, backend=backend, optimization_level=1)
    job = sampler.run([(qc_transpiled,)], shots=shots)
    job_id = str(uuid.uuid4())
    return job_id, job, backend.name


def get_job_status_and_result(job: object) -> tuple[str, dict | None]:
    """Poll job: return (status_str, result_dict or None). status_str in QUEUED, RUNNING, DONE, ERROR."""
    try:
        status = job.status()
        status_str = str(getattr(status, "name", status)).upper()
        if "QUEUED" in status_str or "PENDING" in status_str:
            return "QUEUED", None
        if "RUNNING" in status_str or "IN_PROGRESS" in status_str:
            return "RUNNING", None
        if "DONE" in status_str or "COMPLETED" in status_str:
            result = job.result()
            pub_result = result[0] if result else None
            counts = _extract_counts(pub_result) if pub_result else {}
            result_dict = {"counts": {k: int(v) for k, v in counts.items()}}
            # Expose workload summary when present (e.g. from Qiskit Functions: CPU/QPU time per stage)
            try:
                metadata = getattr(result, "metadata", None)
                if metadata is None and isinstance(result, dict):
                    metadata = result.get("metadata")
                if metadata and isinstance(metadata, dict):
                    ru = metadata.get("resource_usage")
                    if isinstance(ru, dict):
                        result_dict["resource_usage"] = ru
            except Exception:
                pass
            return "DONE", result_dict
        if "ERROR" in status_str or "FAILED" in status_str:
            return "ERROR", {"error": str(getattr(status, "value", status))}
    except Exception as e:
        return "ERROR", {"error": str(e)}
    return "UNKNOWN", None


def get_ibm_job_id(job: object) -> str | None:
    """Return the IBM runtime job id for this job (for Redis/store)."""
    if job is None:
        return None
    jid = getattr(job, "job_id", None)
    if callable(jid):
        return jid()
    return str(jid) if jid is not None else None


def get_job_status_and_result_by_ibm_job_id(ibm_job_id: str, ibm_token: str | None = None) -> tuple[str, dict | None]:
    """Retrieve job from IBM by id and return (status_str, result_dict). Use when job state is in Redis (multi-worker)."""
    try:
        from qiskit_ibm_runtime import QiskitRuntimeService
        token = ibm_token or os.environ.get(IBM_QUANTUM_TOKEN_ENV)
        if not token:
            return "ERROR", {"error": "IBM token not set"}
        service = QiskitRuntimeService(channel=IBM_CHANNEL, token=token)
        job = service.job(ibm_job_id)
        return get_job_status_and_result(job)
    except Exception as e:
        return "ERROR", {"error": str(e)}


def get_hardware_sampler_and_pass_manager(backend_name: str | None = None, ibm_token: str | None = None):
    """Get (sampler, pass_manager, backend) for real IBM hardware; (None, None, None) on failure."""
    try:
        from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
        from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
    except ImportError as e:
        print(f"  Real hardware requires qiskit-ibm-runtime: {e}", file=sys.stderr)
        return None, None, None

    token = ibm_token or os.environ.get(IBM_QUANTUM_TOKEN_ENV)
    if not token:
        print(f"  No IBM Quantum token. Set env {IBM_QUANTUM_TOKEN_ENV}.", file=sys.stderr)
        return None, None, None

    try:
        service = QiskitRuntimeService(channel=IBM_CHANNEL, token=token)
        backend = service.backend(backend_name) if backend_name else service.least_busy(simulator=False, operational=True)
        if backend is None:
            print("  No operational real backend found.", file=sys.stderr)
            return None, None, None
        pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
        sampler = SamplerV2(backend)
        return sampler, pm, backend
    except Exception as e:
        print(f"  Failed to connect to IBM Quantum: {e}", file=sys.stderr)
        return None, None, None


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ASIC protocol on IBM Quantum or simulator")
    parser.add_argument(
        "--protocol",
        type=str,
        default="teleport",
        choices=["teleport", "bell", "commitment", "thief"],
        help="Protocol to run (default: teleport)",
    )
    parser.add_argument(
        "--hardware",
        action="store_true",
        help="Run on real IBM Quantum hardware (requires qiskit-ibm-runtime and IBM_QUANTUM_TOKEN)",
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
        help=f"IBM Quantum token (default: env {IBM_QUANTUM_TOKEN_ENV}). Ignored unless --hardware.",
    )
    parser.add_argument(
        "--shots",
        type=int,
        default=1024,
        metavar="N",
        help="Shots per run (default 1024). Single job, minimal cost.",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        metavar="FILE",
        help="Write backend name, counts, timestamp to JSON file.",
    )
    args = parser.parse_args()

    ops = get_protocol_ops(args.protocol)
    qc = asic_ops_to_qiskit_circuit(ops)
    n_qubits = qc.num_qubits

    backend_name_for_output = None
    counts = None

    if args.hardware:
        sampler, pm, backend = get_hardware_sampler_and_pass_manager(args.backend, ibm_token=args.token)
        if sampler is None or pm is None:
            print("  Falling back to simulation.", file=sys.stderr)
            args.hardware = False
        else:
            backend_name_for_output = backend.name
            print(f"  Running on backend: {backend_name_for_output} ({args.shots} shots)")
            from qiskit import transpile
            qc_transpiled = transpile(qc, backend=backend)
            job = sampler.run([(qc_transpiled,)], shots=args.shots)
            result = job.result()
            pub_result = result[0]
            counts = _extract_counts(pub_result)

    if not args.hardware:
        try:
            from qiskit.primitives import StatevectorSampler
            sampler_sim = StatevectorSampler(seed=42)
        except ImportError:
            from qiskit.primitives import Sampler
            sampler_sim = Sampler()
        print(f"  Running in simulation ({args.shots} shots)")
        job = sampler_sim.run([(qc,)], shots=args.shots)
        result = job.result()
        pub_result = result[0]
        counts = _extract_counts(pub_result)

    if counts is None:
        print("  No counts returned.", file=sys.stderr)
        sys.exit(1)

    print(f"  Protocol: {args.protocol}, qubits: {n_qubits}")
    print(f"  Counts: {counts}")

    if args.output:
        out = {
            "protocol": args.protocol,
            "num_qubits": n_qubits,
            "shots": args.shots,
            "backend": backend_name_for_output,
            "counts": {k: int(v) for k, v in counts.items()},
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(out, f, indent=2)
            print(f"  Result written to {args.output}")
        except OSError as e:
            print(f"  Error writing output: {e}", file=sys.stderr)
            sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
