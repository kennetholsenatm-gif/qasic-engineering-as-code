"""
Pseudo-schedule: dict representation when Qiskit Pulse is not installed.
Used for tests and serialization; can be consumed by QICK export or other backends.
"""
from __future__ import annotations

from typing import Any


def build_pseudo_schedule(ops: list[Any], backend_config: dict[str, Any]) -> dict[str, Any]:
    """
    Build a serializable schedule dict: list of instructions with channel, t0, duration, amplitude.
    """
    dt = backend_config.get("dt", 1e-9)  # seconds per sample
    # Default: 32 samples per single-qubit gate, 64 for CNOT
    samples_1q = int(backend_config.get("samples_per_1q_gate", 32))
    samples_2q = int(backend_config.get("samples_per_2q_gate", 64))
    instructions = []
    t0 = 0
    n_qubits = backend_config.get("n_qubits", 3)
    for op in ops:
        gate = getattr(op, "gate", op.get("gate") if isinstance(op, dict) else None)
        targets = getattr(op, "targets", op.get("targets", []) if isinstance(op, dict) else [])
        param = getattr(op, "param", op.get("param") if isinstance(op, dict) else None)
        if not gate or targets is None:
            continue
        if gate in ("H", "X", "Z", "Rx"):
            duration = samples_1q
            for q in targets:
                if 0 <= q < n_qubits:
                    instructions.append({
                        "channel": f"d{q}",
                        "t0": t0,
                        "duration": duration,
                        "gate": gate,
                        "qubit": q,
                        "param": param,
                    })
        elif gate == "CNOT" and len(targets) >= 2:
            duration = samples_2q
            c, t = targets[0], targets[1]
            if 0 <= c < n_qubits and 0 <= t < n_qubits:
                instructions.append({
                    "channel": f"u{c}_{t}",
                    "t0": t0,
                    "duration": duration,
                    "gate": "CNOT",
                    "control": c,
                    "target": t,
                })
        t0 += samples_2q if gate == "CNOT" else samples_1q
    return {
        "version": "pseudo_v1",
        "dt": dt,
        "n_qubits": n_qubits,
        "instructions": instructions,
        "total_samples": t0,
    }
