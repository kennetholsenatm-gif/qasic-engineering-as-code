"""
Bayesian-Quantum Traffic Controller: main pipeline loop.
Orchestrates telemetry ingest -> Bayesian inference -> Quantum optimizer -> Actuator.
"""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

# Component 1: Data Collection & Aggregation
from data_plane.service import (
    create_telemetry_buffer,
    start_telemetry_collectors,
)

# Component 2: Quantum Pre-processing
from preproc.service import compute_bandwidth_matrix

# Component 3: Quantum Processing
from quantum_core.service import (
    optimize_paths,
    build_directives,
    apply_decisions,
)


def load_config(config_dir: Optional[Path] = None) -> Tuple[dict, dict]:
    """Load pipeline.yaml and topology.yaml."""
    config_dir = config_dir or Path(__file__).resolve().parent / "config"
    with open(config_dir / "pipeline.yaml") as f:
        pipeline_cfg = yaml.safe_load(f) or {}
    with open(config_dir / "topology.yaml") as f:
        topology_cfg = yaml.safe_load(f) or {}
    return pipeline_cfg, topology_cfg


def run_one_cycle(
    buffer: Any,
    pipeline_cfg: dict,
    topology_cfg: dict,
) -> List[dict]:
    """Run a single pipeline cycle: inference -> quantum -> actuator (or dry-run)."""
    telemetry_cfg = pipeline_cfg.get("telemetry", {})
    bayesian_cfg = pipeline_cfg.get("bayesian", {})
    quantum_cfg = pipeline_cfg.get("quantum", {})
    actuator_cfg = pipeline_cfg.get("actuator", {})

    vnis = topology_cfg.get("vnis") or [10001, 10002, 10003]
    paths = topology_cfg.get("paths") or [{"id": "path0", "capacity_mbps": 10000}]
    path_ids = [p["id"] for p in paths]
    path_capacities = [p.get("capacity_mbps", 10000) for p in paths]
    leafs = topology_cfg.get("leafs") or []

    # Component 2: Quantum Pre-processing (Bayesian inference)
    bandwidth_matrix = compute_bandwidth_matrix(
        buffer,
        vnis=vnis,
        path_ids=path_ids,
        bayesian_cfg=bayesian_cfg,
    )
    # Convert path capacities to bytes/sec for QUBO (Mbps -> bytes/sec)
    path_caps_bytes = [c * 1e6 / 8.0 for c in path_capacities]

    # Component 3: Quantum Processing (QAOA + actuator)
    vni_to_path = optimize_paths(
        bandwidth_matrix,
        path_caps_bytes,
        vnis=vnis,
        path_ids=path_ids,
        quantum_cfg=quantum_cfg,
    )
    directives = build_directives(
        vni_to_path,
        path_ids,
        leafs,
    )
    results = apply_decisions(
        directives,
        leafs,
        actuator_cfg=actuator_cfg,
    )
    return results


def main() -> None:
    """Start telemetry collectors and run pipeline loop."""
    pipeline_cfg, topology_cfg = load_config()
    telemetry_cfg = pipeline_cfg.get("telemetry", {})
    pipeline_interval = pipeline_cfg.get("pipeline", {}).get("interval_seconds", 300)
    window_sec = telemetry_cfg.get("window_seconds", 600)

    buffer = create_telemetry_buffer(window_seconds=window_sec)

    # Start collectors in background
    start_telemetry_collectors(
        buffer,
        sflow_port=telemetry_cfg.get("sflow_port", 6343),
        netflow_port=telemetry_cfg.get("netflow_port", 2055),
    )

    print("Bayesian-Quantum Traffic Controller running. Pipeline interval:", pipeline_interval, "s")
    while True:
        try:
            results = run_one_cycle(buffer, pipeline_cfg, topology_cfg)
            for r in results:
                print("Leaf", r.get("leaf"), ":", r.get("status"), r.get("message", ""))
        except Exception as e:
            print("Pipeline cycle error:", e)
        time.sleep(pipeline_interval)


if __name__ == "__main__":
    main()
