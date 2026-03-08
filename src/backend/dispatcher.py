"""
Hybrid Compute Dispatcher: routes DAG nodes to the appropriate compute resource.

When the WUI submits a DAG, the dispatcher parses each node, determines the required
compute resource (classical simulation, FDTD/MEEP-style, or quantum backend), and
delegates to the matching executor (local subprocess, IBM QPU, or future EKS).

Compute resources:
- CLASSICAL_SIM: Pure Python/NumPy simulation (QKD, quantum illumination, quantum radar, protocol sim).
- FDTD: Finite-difference / inverse-design / MEEP-style workloads (routing, inverse_design, HEaC, thermal).
- QUANTUM_BACKEND: Real quantum hardware (IBM QPU) for protocol_teleport, routing --hardware.
- EKS: Future AWS EKS or other Kubernetes-backed workers.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.backend.task_registry import (
    BACKEND_LOCAL,
    BACKEND_IBM_QPU,
    BACKEND_AWS_EKS,
    get_task_type,
    COMPUTE_CLASSICAL_SIM,
    COMPUTE_FDTD,
    COMPUTE_QUANTUM_BACKEND,
    COMPUTE_EKS,
)


def resolve_compute_resource(task_type_id: str, backend: str) -> str:
    """
    Determine the compute resource type for a task type and backend choice.
    Uses task_registry.compute_resource when present; otherwise infers from backend and task type.
    Returns one of COMPUTE_* constants.
    """
    if backend == BACKEND_IBM_QPU:
        return COMPUTE_QUANTUM_BACKEND
    if backend == BACKEND_AWS_EKS:
        return COMPUTE_EKS

    tt = get_task_type(task_type_id)
    if tt and "compute_resource" in tt:
        return tt["compute_resource"]

    # Fallback: classify by workload for local backend
    fdt_like = {
        "routing", "inverse_design", "heac_library", "heac_phases_to_geometry",
        "manifest_to_gds", "thermal",
    }
    return COMPUTE_FDTD if task_type_id in fdt_like else COMPUTE_CLASSICAL_SIM


def dispatch(
    task_type: str,
    config: dict,
    inputs: dict,
    work_dir: Path,
) -> tuple[dict[str, Any], str | None]:
    """
    Single entry point for the Hybrid Compute Dispatcher.
    Resolves compute resource, delegates to the appropriate executor, and returns (outputs, error).
    """
    from src.backend.executor import _execute_local, _execute_ibm

    tt = get_task_type(task_type)
    if not tt:
        return {}, f"Unknown task_type: {task_type}"

    backend = config.get("backend", BACKEND_LOCAL)
    resource = resolve_compute_resource(task_type, backend)

    if backend == BACKEND_LOCAL:
        outputs, err = _execute_local(task_type, config, inputs, work_dir)
    elif backend == BACKEND_IBM_QPU:
        outputs, err = _execute_ibm(task_type, config, inputs)
    elif backend == BACKEND_AWS_EKS:
        err = "EKS backend not configured"
        outputs = {}
    else:
        err = f"Unknown backend: {backend}"
        outputs = {}

    return outputs, err
