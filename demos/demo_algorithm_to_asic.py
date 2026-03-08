"""
Demo: Algorithm-to-ASIC pipeline on 4-qubit GHZ (and optional QFT).
Generates OpenQASM, runs qasm_to_asic_pipeline, prints summary of physical qubits,
custom edges, and heavily-used bus resonators (by L_kinetic_nH).
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# Run from repo root: python demos/demo_algorithm_to_asic.py
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.core_compute.engineering.qasm_to_asic_pipeline import run_qasm_to_asic


# 4-qubit GHZ: H(0), CNOT(0,1), CNOT(1,2), CNOT(2,3)
GHZ_4_QASM = """
OPENQASM 2.0;
qreg q[4];
h q[0];
cx q[0], q[1];
cx q[1], q[2];
cx q[2], q[3];
"""

# 4-qubit QFT (simplified: Hadamards + controlled phases, no swaps for brevity)
QFT_4_QASM = """
OPENQASM 2.0;
qreg q[4];
h q[0];
h q[1];
h q[2];
h q[3];
cx q[0], q[1];
cx q[1], q[2];
cx q[2], q[3];
cx q[0], q[2];
cx q[0], q[3];
cx q[1], q[3];
"""


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="qasm_to_asic_") as tmp:
        out_dir = tmp
        print("Running Algorithm-to-ASIC pipeline on 4-qubit GHZ...")
        result = run_qasm_to_asic(
            qasm_string=GHZ_4_QASM,
            output_dir=out_dir,
            circuit_name="ghz_4",
        )

    n_nodes = len(result.get("nodes", []))
    edges = result.get("edges", [])
    n_edges = len(edges)

    print("\n--- Summary ---")
    print(f"Physical qubits (nodes): {n_nodes}")
    print(f"Custom edges (trace connections): {n_edges}")
    if edges:
        print("Edge list (node i, j, L_kinetic_nH):")
        for e in edges[:15]:
            print(f"  {e}")
        if n_edges > 15:
            print(f"  ... and {n_edges - 15} more")

    # Heavily-used bus resonators: nodes with highest L_kinetic_nH (from extraction)
    nodes_list = result.get("nodes", [])
    sorted_nodes = sorted(
        enumerate(nodes_list),
        key=lambda x: -(x[1].get("L_kinetic_nH", 0.0)),
    )
    print("\nHeavily-used bus resonators (by L_kinetic_nH, top 5):")
    for node_idx, n in sorted_nodes[:5]:
        L = n.get("L_kinetic_nH", 0.0)
        print(f"  Node {node_idx}: L_kinetic_nH = {L:.6f} nH")

    sorted_edges = sorted(edges, key=lambda x: -x.get("L_kinetic_nH", 0.0))
    print("\nEdges by L_kinetic_nH (top 5):")
    for e in sorted_edges[:5]:
        print(f"  ({e.get('i')}, {e.get('j')}): L_kinetic_nH = {e.get('L_kinetic_nH', 0):.6f}")

    manifest_path = result.get("_custom_asic_manifest_path", "")
    print(f"\nCustom ASIC manifest written to: {manifest_path}")

    assert "nodes" in result and "edges" in result and result.get("source") == "superconducting_extraction"
    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
