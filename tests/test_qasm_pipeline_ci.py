"""
CI smoke test: run OpenQASM 2.0 and 3.0 through the Algorithm-to-ASIC pipeline.
Used by .github/workflows/hardware-ci.yml job "OpenQASM 2.0 / 3.0 → ASIC pipeline".
"""
from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path

import pytest

from src.core_compute.engineering.qasm_to_asic_pipeline import run_qasm_to_asic

HAVE_QASM3 = importlib.util.find_spec("qiskit.qasm3") is not None

QASM2 = """OPENQASM 2.0;
qreg q[3];
h q[0];
cx q[0], q[1];
z q[0];
"""

QASM3 = """OPENQASM 3.0;
include "stdgates.inc";
qubit[3] q;
h q[0];
cx q[0], q[1];
z q[0];
"""


def test_qasm2_algorithm_to_asic_pipeline():
    """Run OpenQASM 2.0 through run_qasm_to_asic; assert manifest is produced."""
    with tempfile.TemporaryDirectory(prefix="ci_qasm2_") as out_dir:
        r = run_qasm_to_asic(
            qasm_string=QASM2,
            output_dir=out_dir,
            circuit_name="ci_2",
        )
        assert "_custom_asic_manifest_path" in r
        assert Path(r["_custom_asic_manifest_path"]).exists()


@pytest.mark.skipif(not HAVE_QASM3, reason="qiskit-qasm3-import not installed")
def test_qasm3_algorithm_to_asic_pipeline():
    """Run OpenQASM 3.0 through run_qasm_to_asic when qiskit.qasm3 is available."""
    with tempfile.TemporaryDirectory(prefix="ci_qasm3_") as out_dir:
        r = run_qasm_to_asic(
            qasm_string=QASM3,
            output_dir=out_dir,
            circuit_name="ci_3",
        )
        assert "_custom_asic_manifest_path" in r
        assert Path(r["_custom_asic_manifest_path"]).exists()
