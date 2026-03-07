"""Tests for engineering.viz_routing_phase: load_json, main with fixtures; regression for missing phase keys."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

import sys

from engineering.viz_routing_phase import load_json, main


def test_load_json_valid():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"num_logical_qubits": 3, "solver": "QAOA"}, f)
        path = f.name
    try:
        data = load_json(path)
        assert data["num_logical_qubits"] == 3
        assert data["solver"] == "QAOA"
    finally:
        Path(path).unlink(missing_ok=True)


def test_load_json_missing_file_raises():
    with pytest.raises(FileNotFoundError, match="not found"):
        load_json("/nonexistent/file.json")


def test_load_json_invalid_json_raises():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("not json")
        path = f.name
    try:
        with pytest.raises(ValueError, match="Invalid JSON"):
            load_json(path)
    finally:
        Path(path).unlink(missing_ok=True)


def test_main_with_inverse_missing_phase_keys_does_not_crash(capsys):
    """Regression: inverse JSON with missing phase_min/phase_max/phase_mean should print '?' not crash."""
    with tempfile.TemporaryDirectory() as tmp:
        routing_path = Path(tmp) / "routing.json"
        inverse_path = Path(tmp) / "inverse.json"
        json.dump({
            "num_logical_qubits": 3,
            "num_physical_nodes": 3,
            "solver": "QAOA",
            "objective_value": 4.0,
            "mapping": [{"logical": 0, "physical": 0}, {"logical": 1, "physical": 1}, {"logical": 2, "physical": 2}],
        }, open(routing_path, "w"))
        # Inverse with no phase_min/phase_max/phase_mean
        json.dump({
            "device": "cpu",
            "num_meta_atoms": 100,
            # omit phase_min, phase_max, phase_mean
        }, open(inverse_path, "w"))
        # Run main; should exit 0 and print ? for phase stats
        old_argv = sys.argv
        try:
            sys.argv = ["viz_routing_phase.py", str(routing_path), "--inverse", str(inverse_path)]
            exit_code = main()
            assert exit_code == 0
            out = capsys.readouterr()
            assert "Phase min" in out.out
            assert "Phase max" in out.out
            assert "Phase mean" in out.out
            # Should show ? for missing values (no TypeError)
            assert "?" in out.out or "rad" in out.out
        finally:
            sys.argv = old_argv


def test_main_routing_only_succeeds(capsys):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({
            "num_logical_qubits": 3,
            "num_physical_nodes": 3,
            "solver": "QAOA",
            "objective_value": 4.0,
            "mapping": [{"logical": 0, "physical": 0}, {"logical": 1, "physical": 1}, {"logical": 2, "physical": 2}],
        }, f)
        path = f.name
    try:
        old_argv = sys.argv
        try:
            sys.argv = ["viz_routing_phase.py", path]
            exit_code = main()
            assert exit_code == 0
            out = capsys.readouterr().out
            assert "Routing" in out
            assert "3" in out
        finally:
            sys.argv = old_argv
    finally:
        Path(path).unlink(missing_ok=True)
