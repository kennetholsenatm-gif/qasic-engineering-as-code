"""Tests for engineering.run_protocol_on_ibm: ASIC ops to Qiskit, protocol run in simulation."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

import pytest

# Add repo root for asic import when importing the module under test
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from asic.circuit import Op, protocol_teleport_ops, protocol_commitment_ops

try:
    from engineering.run_protocol_on_ibm import (
        asic_ops_to_qiskit_circuit,
        get_protocol_ops,
        _extract_counts,
        bell_ops,
    )
    HAS_PROTOCOL_IBM = True
except ImportError as e:
    HAS_PROTOCOL_IBM = False
    _import_err = e


@pytest.mark.skipif(not HAS_PROTOCOL_IBM, reason="run_protocol_on_ibm or asic not available")
def test_asic_ops_to_qiskit_circuit_bell():
    """Bell circuit H(0), CNOT(0,1) produces a 2-qubit circuit with measure_all."""
    ops = bell_ops()
    qc = asic_ops_to_qiskit_circuit(ops)
    assert qc.num_qubits == 2
    assert qc.num_clbits == 2
    # Gate count: 2 (H, CNOT) + measurements
    assert qc.size() >= 2


@pytest.mark.skipif(not HAS_PROTOCOL_IBM, reason="run_protocol_on_ibm or asic not available")
def test_asic_ops_to_qiskit_circuit_teleport():
    """Teleport protocol ops produce a 3-qubit circuit."""
    ops = protocol_teleport_ops()
    qc = asic_ops_to_qiskit_circuit(ops)
    assert qc.num_qubits == 3
    assert qc.num_clbits == 3


@pytest.mark.skipif(not HAS_PROTOCOL_IBM, reason="run_protocol_on_ibm or asic not available")
def test_get_protocol_ops():
    """get_protocol_ops returns correct op lists."""
    assert len(get_protocol_ops("teleport")) == 4
    assert len(get_protocol_ops("bell")) == 2
    assert len(get_protocol_ops("commitment")) == 2
    assert len(get_protocol_ops("thief")) == 5  # teleport + Rx
    with pytest.raises(ValueError, match="Unknown protocol"):
        get_protocol_ops("invalid")


@pytest.mark.skipif(not HAS_PROTOCOL_IBM, reason="run_protocol_on_ibm or asic not available")
def test_extract_counts_fallback():
    """_extract_counts handles missing or empty data."""
    class EmptyData:
        pass
    empty = type("PubResult", (), {"data": EmptyData})()
    assert _extract_counts(empty) == {}


@pytest.mark.skipif(not HAS_PROTOCOL_IBM, reason="run_protocol_on_ibm or asic not available")
def test_run_protocol_on_ibm_simulation_exits_zero_and_writes_json():
    """Running the script in simulation with -o produces valid JSON with expected keys."""
    with tempfile.TemporaryDirectory() as tmp:
        out_path = os.path.join(tmp, "protocol_out.json")
        cmd = [
            sys.executable,
            os.path.join(_REPO_ROOT, "engineering", "run_protocol_on_ibm.py"),
            "--protocol", "teleport",
            "--shots", "64",
            "-o", out_path,
        ]
        env = os.environ.copy()
        env["PYTHONPATH"] = _REPO_ROOT
        result = subprocess.run(cmd, cwd=_REPO_ROOT, env=env, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, (result.stdout, result.stderr)
        assert os.path.isfile(out_path)
        with open(out_path, encoding="utf-8") as f:
            data = json.load(f)
        assert "protocol" in data
        assert data["protocol"] == "teleport"
        assert "num_qubits" in data
        assert data["num_qubits"] == 3
        assert "counts" in data
        assert "timestamp" in data
        assert sum(data["counts"].values()) == 64
