"""
End-to-end Algorithm-to-ASIC pipeline: load OpenQASM, extract interaction graph,
synthesize custom Topology and geometry manifest, run superconducting extraction,
and save custom ASIC manifest for downstream thermodynamic/FEA simulations.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from ..asic.qasm_loader import (
    interaction_graph_from_qasm_path,
    interaction_graph_from_qasm_string,
)
from ..asic.topology_builder import (
    build_topology_from_interaction_graph,
    geometry_manifest_from_interaction_graph,
)
from .superconducting_extraction import extract_kinetic_inductance


def run_qasm_to_asic(
    qasm_path: str | None = None,
    qasm_string: str | None = None,
    output_dir: str | None = None,
    circuit_name: str | None = None,
    pitch_um: float = 1.0,
    decompose_to_asic: bool = False,
) -> dict[str, Any]:
    """
    Run the full pipeline: QASM -> interaction graph -> Topology + geometry manifest
    -> superconducting extraction -> custom ASIC manifest.
    Either qasm_path or qasm_string must be provided.
    When decompose_to_asic is True, unsupported gates (T, S, Rz, U3, etc.) are transpiled to H, X, Z, Rx, CNOT.
    Returns the extraction result dict (nodes, edges, jj, gamma1, gamma2, L_kinetic_nH, etc.).
    Output file format matches what downstream thermodynamic/FEA simulations expect.
    """
    if qasm_path is None and qasm_string is None:
        raise ValueError("Provide either qasm_path or qasm_string")
    if qasm_path is not None and qasm_string is not None:
        raise ValueError("Provide only one of qasm_path or qasm_string")

    if output_dir is None:
        output_dir = os.getcwd()
    os.makedirs(output_dir, exist_ok=True)
    out_path = Path(output_dir)

    if qasm_path is not None:
        graph = interaction_graph_from_qasm_path(qasm_path, decompose_to_asic=decompose_to_asic)
        if circuit_name is None:
            circuit_name = Path(qasm_path).stem or "circuit"
    else:
        graph = interaction_graph_from_qasm_string(qasm_string, decompose_to_asic=decompose_to_asic)
        if circuit_name is None:
            circuit_name = "circuit"

    topo = build_topology_from_interaction_graph(graph)
    geom_manifest = geometry_manifest_from_interaction_graph(graph, pitch_um=pitch_um)

    geom_path = out_path / f"{circuit_name}_geometry_manifest.json"
    with open(geom_path, "w", encoding="utf-8") as f:
        json.dump(geom_manifest, f, indent=2)

    result = extract_kinetic_inductance(
        str(geom_path),
        routing_path=None,
    )

    custom_path = out_path / f"{circuit_name}_custom_asic_manifest.json"
    with open(custom_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    result["_custom_asic_manifest_path"] = str(custom_path)
    result["_geometry_manifest_path"] = str(geom_path)
    result["_topology"] = topo
    result["_interaction_graph"] = graph
    return result  # callers can use _topology / _interaction_graph; file has only extraction keys


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Algorithm-to-ASIC: QASM -> interaction graph -> custom topology + superconducting extraction.",
    )
    parser.add_argument("--qasm", type=str, default=None, help="Path to .qasm file")
    parser.add_argument("--qasm-string", type=str, default=None, dest="qasm_string", help="OpenQASM source string")
    parser.add_argument("-o", "--output-dir", type=str, default=None, dest="output_dir", help="Output directory (default: cwd)")
    parser.add_argument("--name", type=str, default=None, dest="circuit_name", help="Circuit name for output files (default: from path or 'circuit')")
    parser.add_argument("--pitch-um", type=float, default=1.0, help="Pitch in um for geometry manifest")
    args = parser.parse_args()

    if args.qasm is None and args.qasm_string is None:
        print("Error: provide --qasm or --qasm-string", file=sys.stderr)
        return 1

    try:
        result = run_qasm_to_asic(
            qasm_path=args.qasm,
            qasm_string=args.qasm_string,
            output_dir=args.output_dir,
            circuit_name=args.circuit_name,
            pitch_um=args.pitch_um,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    path = result.get("_custom_asic_manifest_path", "")
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
