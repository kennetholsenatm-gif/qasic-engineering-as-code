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

from asic.circuit import Op, protocol_teleport_ops, protocol_commitment_ops, protocol_thief_ops

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
