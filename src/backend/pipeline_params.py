"""
Pipeline run parameters for the DAG orchestrator. Mirrors run_pipeline.py CLI.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PipelineParams:
    """Options for the metasurface pipeline (routing -> inverse -> HEaC -> GDS -> ...)."""
    output_base: str = "pipeline_result"
    device: str = "auto"
    model: str = "mlp"
    routing_method: str = "qaoa"
    skip_routing: bool = False
    skip_inverse: bool = False
    fast: bool = False
    hardware: bool = False
    with_superscreen: bool = False
    heac: bool = False
    heac_library: Optional[str] = None
    pdk: bool = False
    pdk_config: Optional[str] = None
    gds: bool = False
    drc: bool = False
    lvs: bool = False
    dft: bool = False
    thermal: bool = False
    parasitic: bool = False
    meep_verify: bool = False
    packaging: bool = False
    num_qubits: Optional[int] = None  # Required for standalone routing (no circuit). Circuit-driven pipeline derives from OpenQASM.
    # Resolved at runtime (repo root, script_dir)
    repo_root: str = ""
    script_dir: str = ""

    def routing_json(self) -> str:
        return os.path.join(self.script_dir, f"{self.output_base}_routing.json")

    def inverse_json(self) -> str:
        return os.path.join(self.script_dir, f"{self.output_base}_inverse.json")

    def npy_path(self) -> str:
        return os.path.join(self.script_dir, f"{self.output_base}_inverse_phases.npy")

    def inductance_json(self) -> str:
        return os.path.join(self.script_dir, f"{self.output_base}_inductance.json")

    def manifest_path(self) -> str:
        return os.path.join(self.script_dir, f"{self.output_base}_geometry_manifest.json")

    def gds_path(self) -> str:
        return os.path.join(self.script_dir, f"{self.output_base}.gds")
