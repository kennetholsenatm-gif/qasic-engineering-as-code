"""
Export pulse schedule to QICK (Quantum Instrumentation Control Kit) compatible format.
Consumes the same schedule dict from compiler (pseudo or OpenPulse summary).
Ref: NEXT_STEPS_ROADMAP.md §2.1 Target FPGA/AWG Backends.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def schedule_to_qick(schedule: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Convert schedule (pseudo or dict with instructions) to QICK-compatible structure.
    Returns dict: waveform_defs, channel_map, timing_ns, dt_ns.
    """
    config = config or {}
    dt_ns = (schedule.get("dt", 1e-9) or 1e-9) * 1e9
    instructions = schedule.get("instructions", [])
    n_qubits = schedule.get("n_qubits", config.get("n_qubits", 3))
    waveform_defs: list[dict[str, Any]] = []
    channel_map: list[dict[str, Any]] = []
    t_max_ns = 0
    for ix, inst in enumerate(instructions):
        ch = inst.get("channel", f"d{inst.get('qubit', 0)}")
        t0 = inst.get("t0", 0)
        duration = inst.get("duration", 32)
        t_ns = t0 * dt_ns
        length_ns = duration * dt_ns
        t_max_ns = max(t_max_ns, t_ns + length_ns)
        # QICK-style: envelope (placeholder shape), freq, phase, gain
        waveform_defs.append({
            "id": ix,
            "channel": ch,
            "t_start_ns": round(t_ns, 2),
            "length_ns": round(length_ns, 2),
            "gate": inst.get("gate", "pulse"),
            "qubit": inst.get("qubit", inst.get("control", inst.get("target", 0))),
        })
        if ch not in [c.get("channel") for c in channel_map]:
            channel_map.append({"channel": ch, "type": "drive"})
    return {
        "version": "qasic_qick_v1",
        "dt_ns": dt_ns,
        "n_qubits": n_qubits,
        "waveform_defs": waveform_defs,
        "channel_map": channel_map,
        "total_time_ns": round(t_max_ns, 2),
    }


def write_qick_config(schedule: dict[str, Any], output_path: str, config: dict[str, Any] | None = None) -> None:
    """Write QICK-compatible JSON to output_path."""
    qick = schedule_to_qick(schedule, config)
    Path(output_path).write_text(json.dumps(qick, indent=2), encoding="utf-8")
