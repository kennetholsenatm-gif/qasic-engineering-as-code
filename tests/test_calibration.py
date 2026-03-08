"""Tests for engineering.calibration: digital twin, Bayesian update, schema."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def test_telemetry_schema_validate():
    from engineering.calibration.telemetry_schema import validate_telemetry
    valid, errs = validate_telemetry({})
    assert valid is True
    valid, errs = validate_telemetry({"qubits": [{"T1_us": 50, "T2_us": 30}]})
    assert valid is True
    valid, errs = validate_telemetry({"qubits": "not a list"})
    assert valid is False


def test_digital_twin_to_json():
    from engineering.calibration.digital_twin import DigitalTwin
    import numpy as np
    twin = DigitalTwin(n_nodes=3, decoherence_rates=np.array([0.1, 0.2, 0.15]))
    out = twin.to_decoherence_json()
    assert "nodes" in out
    assert len(out["nodes"]) == 3
    assert out["nodes"][0]["gamma1"] == 0.1
    assert out["source"] == "digital_twin"


def test_bayesian_update_synthetic():
    from engineering.calibration.bayesian_update import update_decoherence_from_telemetry
    from engineering.calibration.digital_twin import DigitalTwin
    telemetry_list = [
        {"qubits": [{"index": 0, "T1_us": 100, "T2_us": 50}, {"index": 1, "T2_us": 40}, {"index": 2, "T2_us": 60}]},
        {"qubits": [{"index": 0, "T2_us": 55}, {"index": 1, "T2_us": 38}, {"index": 2, "T2_us": 58}]},
    ]
    twin = update_decoherence_from_telemetry(telemetry_list, n_nodes=3)
    assert twin.n_nodes == 3
    # Rates ~ 1/T2: 1/50, 1/40, 1/60 etc -> averaged
    assert twin.decoherence_rates[0] > 0
    assert twin.decoherence_rates[1] > twin.decoherence_rates[2]


def test_run_calibration_cycle(tmp_path):
    from engineering.calibration.run_calibration_cycle import run_calibration_cycle
    telemetry_file = tmp_path / "telemetry.json"
    telemetry_file.write_text(json.dumps({
        "qubits": [
            {"index": 0, "T1_us": 50, "T2_us": 30},
            {"index": 1, "T2_us": 25},
            {"index": 2, "T2_us": 35},
        ],
    }), encoding="utf-8")
    out_file = tmp_path / "decoherence.json"
    rc = run_calibration_cycle(str(telemetry_file), str(out_file), n_nodes=3)
    assert rc == 0
    assert out_file.exists()
    data = json.loads(out_file.read_text())
    assert len(data["nodes"]) == 3
    assert data["source"] == "digital_twin"
