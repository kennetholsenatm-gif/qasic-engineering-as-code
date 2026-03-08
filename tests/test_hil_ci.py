"""
HIL-style CI assertions: schedule has expected instruction count, calibration exit 0,
routing with calibration decoherence produces valid mapping.
Ref: NEXT_STEPS_ROADMAP.md §2.2 Hardware-in-the-Loop CI.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
ENGINEERING = REPO_ROOT / "src" / "core_compute" / "engineering"


def test_hil_schedule_has_instructions(tmp_path):
    """Compile teleport to schedule; assert schedule has instructions."""
    import subprocess
    import sys
    schedule_path = tmp_path / "ci_schedule.json"
    cmd = [sys.executable, "-m", "src.core_compute.pulse", "--circuit", "teleport", "-o", str(schedule_path)]
    rc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=30)
    assert rc.returncode == 0, (rc.stdout or "") + (rc.stderr or "")
    assert schedule_path.exists()
    with open(schedule_path, encoding="utf-8") as f:
        schedule = json.load(f)
    # Pseudo schedule has "instructions" or "pulses"; OpenPulse summary has "num_instructions"
    num_instructions = (
        schedule.get("num_instructions")
        or len(schedule.get("instructions", []))
        or len(schedule.get("pulses", []))
    )
    assert num_instructions is not None and num_instructions >= 1


def test_hil_calibration_cycle_exit_zero(tmp_path):
    """Run calibration cycle with synthetic telemetry; assert exit 0 and output exists."""
    import subprocess
    import sys
    telemetry = ENGINEERING / "ci_baseline" / "ci_synthetic_telemetry.json"
    if not telemetry.exists():
        pytest.skip("ci_synthetic_telemetry.json not found")
    out_path = tmp_path / "decoherence_from_calibration.json"
    cmd = [
        sys.executable, "-m", "src.core_compute.engineering.calibration.run_calibration_cycle",
        str(telemetry),
        "-o", str(out_path),
        "--n-nodes", "3",
    ]
    rc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=30)
    assert rc.returncode == 0, (rc.stdout or "") + (rc.stderr or "")
    assert out_path.exists()
    with open(out_path, encoding="utf-8") as f:
        data = json.load(f)
    assert "nodes" in data
    assert len(data["nodes"]) == 3


def test_hil_routing_with_calibration_decoherence(tmp_path):
    """Run routing with decoherence file from calibration; assert valid mapping."""
    import subprocess
    import sys
    # First produce decoherence file
    telemetry = ENGINEERING / "ci_baseline" / "ci_synthetic_telemetry.json"
    if not telemetry.exists():
        pytest.skip("ci_synthetic_telemetry.json not found")
    decoherence_path = tmp_path / "ci_decoherence.json"
    cal_cmd = [
        sys.executable, "-m", "src.core_compute.engineering.calibration.run_calibration_cycle",
        str(telemetry), "-o", str(decoherence_path), "--n-nodes", "3",
    ]
    rc = subprocess.run(cal_cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=30)
    if rc.returncode != 0:
        pytest.skip("Calibration step failed")
    routing_path = tmp_path / "ci_hil_routing.json"
    route_cmd = [
        sys.executable, "-m", "src.core_compute.engineering.routing_qubo_qaoa",
        "-o", str(routing_path),
        "--decoherence-file", str(decoherence_path),
    ]
    rc = subprocess.run(route_cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120)
    assert rc.returncode == 0, (rc.stdout or "") + (rc.stderr or "")
    assert routing_path.exists()
    with open(routing_path, encoding="utf-8") as f:
        data = json.load(f)
    assert "mapping" in data
    mapping = data["mapping"]
    assert len(mapping) >= 3
    for m in mapping:
        assert "logical" in m and "physical" in m
