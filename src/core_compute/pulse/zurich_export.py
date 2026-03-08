"""
Export pulse schedule to Zurich Instruments compatible format (API/config).
Consumes the same schedule dict from compiler (pseudo or OpenPulse summary).
Ref: NEXT_STEPS_ROADMAP.md §2.1 Target FPGA/AWG Backends.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def schedule_to_zurich(schedule: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Convert schedule to Zurich Instruments style config: sequence of AWG segments.
    Returns dict: awg_channels, segments, sampling_rate_hz, markers.
    """
    config = config or {}
    dt = schedule.get("dt", 1e-9) or 1e-9
    sampling_rate_hz = 1.0 / dt
    instructions = schedule.get("instructions", [])
    n_qubits = schedule.get("n_qubits", config.get("n_qubits", 3))
    segments: list[dict[str, Any]] = []
    channels_seen: set[str] = set()
    for inst in instructions:
        ch = inst.get("channel", f"ch_{inst.get('qubit', 0)}")
        channels_seen.add(ch)
        t0 = inst.get("t0", 0)
        duration = inst.get("duration", 32)
        segments.append({
            "channel": ch,
            "start_sample": t0,
            "length_sample": duration,
            "gate": inst.get("gate", "pulse"),
            "amplitude": 1.0,
            "phase_rad": 0.0,
        })
    return {
        "version": "qasic_zurich_v1",
        "sampling_rate_hz": round(sampling_rate_hz, 0),
        "n_qubits": n_qubits,
        "awg_channels": list(channels_seen),
        "segments": segments,
        "total_samples": schedule.get("total_samples", 0),
    }


def write_zurich_config(schedule: dict[str, Any], output_path: str, config: dict[str, Any] | None = None) -> None:
    """Write Zurich Instruments compatible JSON to output_path."""
    zurich = schedule_to_zurich(schedule, config)
    Path(output_path).write_text(json.dumps(zurich, indent=2), encoding="utf-8")
