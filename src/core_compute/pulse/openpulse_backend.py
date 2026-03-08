"""
Build Qiskit OpenPulse Schedule from ASIC gate ops.
Maps H, X, Z, Rx to single-qubit pulses; CNOT to two-qubit pulse sequence.
"""
from __future__ import annotations

from typing import Any

try:
    from qiskit import pulse
    from qiskit.pulse.library import Gaussian, GaussianSquare
    _HAS_PULSE = True
except ImportError:
    pulse = None
    _HAS_PULSE = False


def build_schedule_openpulse(
    ops: list[Any],
    backend_config: dict[str, Any],
    topology: Any = None,
) -> Any:
    """
    Build a qiskit.pulse.Schedule from gate ops.
    backend_config: n_qubits, dt (optional), duration_1q, duration_2q, amp (optional).
    """
    if not _HAS_PULSE:
        raise ImportError("qiskit.pulse not available; use pseudo_schedule or install qiskit")
    n_qubits = int(backend_config.get("n_qubits", 3))
    dt = backend_config.get("dt", 1e-9)
    duration_1q = int(backend_config.get("duration_1q", 128))
    duration_2q = int(backend_config.get("duration_2q", 256))
    amp = float(backend_config.get("amp", 0.1))
    sigma_1q = duration_1q // 4
    sigma_2q = duration_2q // 4

    # Build a fake backend with n_qubits for pulse.build
    with pulse.build(name="asic_schedule") as sched:
        t0 = 0
        for op in ops:
            gate = getattr(op, "gate", None)
            targets = getattr(op, "targets", [])
            param = getattr(op, "param", None)
            if not gate or not targets:
                continue
            if gate in ("H", "X", "Z"):
                q = targets[0]
                if 0 <= q < n_qubits:
                    chan = pulse.DriveChannel(q)
                    # Simple Gaussian for all; real backend would use different amps/phase for H vs X vs Z
                    pulse.play(
                        Gaussian(duration_1q, amp, sigma_1q),
                        chan,
                    )
                t0 += duration_1q
            elif gate == "Rx" and param is not None:
                q = targets[0]
                if 0 <= q < n_qubits:
                    chan = pulse.DriveChannel(q)
                    # Parametrized amplitude proxy for angle
                    a = amp * (float(param) / 3.14159)
                    pulse.play(
                        Gaussian(duration_1q, a, sigma_1q),
                        chan,
                    )
                t0 += duration_1q
            elif gate == "CNOT" and len(targets) >= 2:
                c, t = targets[0], targets[1]
                if 0 <= c < n_qubits and 0 <= t < n_qubits:
                    dc = pulse.DriveChannel(c)
                    dt_chan = pulse.DriveChannel(t)
                    # Cross-resonance style: drive on control and target
                    pulse.play(
                        GaussianSquare(duration_2q, amp, sigma_2q, duration_2q - 2 * sigma_2q),
                        dc,
                    )
                    pulse.play(
                        Gaussian(duration_2q, amp * 0.5, sigma_2q),
                        dt_chan,
                    )
                t0 += duration_2q
    return sched
