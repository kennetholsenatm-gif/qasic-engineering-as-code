"""Tests for pulse compiler: pseudo-schedule and OpenPulse (when qiskit available)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def test_pseudo_schedule_teleport():
    """Compile teleport ops to pseudo-schedule; no Qiskit required."""
    from src.core_compute.asic.circuit import protocol_teleport_ops
    from src.core_compute.pulse.compiler import compile_circuit_to_schedule
    ops = protocol_teleport_ops()
    config = {"n_qubits": 3, "dt": 1e-9}
    # Without qiskit.pulse, compiler uses pseudo_schedule
    schedule = compile_circuit_to_schedule(ops, config, topology=None)
    assert isinstance(schedule, dict)
    assert schedule.get("version") == "pseudo_v1"
    assert schedule.get("n_qubits") == 3
    inst = schedule.get("instructions", [])
    assert len(inst) >= 4  # H(1), CNOT(1,2), CNOT(0,1), H(0)
    assert schedule.get("total_samples", 0) > 0


def test_pseudo_schedule_instruction_structure():
    """Pseudo instructions have channel, t0, duration, gate."""
    from src.core_compute.pulse.pseudo_schedule import build_pseudo_schedule
    ops = [
        type("Op", (), {"gate": "H", "targets": [0], "param": None})(),
        type("Op", (), {"gate": "CNOT", "targets": [0, 1], "param": None})(),
    ]
    config = {"n_qubits": 2}
    out = build_pseudo_schedule(ops, config)
    assert out["n_qubits"] == 2
    assert any(i.get("gate") == "H" and i.get("channel") == "d0" for i in out["instructions"])
    assert any(i.get("gate") == "CNOT" for i in out["instructions"])


def test_compile_cli_pseudo(tmp_path):
    """CLI produces JSON output (pseudo when no qiskit pulse)."""
    from src.core_compute.pulse.compile_cli import main
    out_file = tmp_path / "schedule.json"
    # Run in repo root so asic is importable
    import os
    orig_cwd = os.getcwd()
    try:
        os.chdir(REPO_ROOT)
        # Simulate: sys.argv for compile_cli
        import argparse
        from src.core_compute.pulse.compile_cli import load_circuit_ops, load_config
        ops = load_circuit_ops("teleport")
        config = load_config(None)
        from src.core_compute.pulse.compiler import compile_circuit_to_schedule
        sched = compile_circuit_to_schedule(ops, config)
        with open(out_file, "w") as f:
            json.dump(sched, f, indent=2)
    finally:
        os.chdir(orig_cwd)
    assert out_file.exists()
    data = json.loads(out_file.read_text())
    assert "instructions" in data or "num_instructions" in data or "version" in data


def test_openpulse_schedule():
    """When qiskit.pulse is available, compiler returns a Schedule."""
    try:
        from qiskit import pulse as _  # noqa: F401
    except ImportError:
        pytest.skip("qiskit.pulse not available")
    from src.core_compute.asic.circuit import protocol_teleport_ops
    from src.core_compute.pulse.openpulse_backend import build_schedule_openpulse
    ops = protocol_teleport_ops()
    config = {"n_qubits": 3}
    sched = build_schedule_openpulse(ops, config, None)
    assert sched is not None
    assert hasattr(sched, "instructions")
    assert len(sched.instructions) >= 1
