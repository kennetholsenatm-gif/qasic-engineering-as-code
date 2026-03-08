"""
Task type registry for the DAG orchestrator.
Defines runnable task types: inputs, outputs, supported backends, and mapping to execution.
"""
from __future__ import annotations

from typing import Any

# Backends the hybrid dispatcher can route to
BACKEND_LOCAL = "local"
BACKEND_IBM_QPU = "ibm_qpu"
BACKEND_AWS_EKS = "aws_eks"

# Compute resource types (for dispatcher and UI)
COMPUTE_CLASSICAL_SIM = "classical_sim"
COMPUTE_FDTD = "fdtf"  # FDTD-style / inverse-design / MEEP
COMPUTE_QUANTUM_BACKEND = "quantum_backend"
COMPUTE_EKS = "eks"

# Port types for FBP data flow
PORT_TYPE_FILE = "file"
PORT_TYPE_JSON = "json"


def _input(name: str, port_type: str = PORT_TYPE_FILE, required: bool = True) -> dict:
    return {"name": name, "type": port_type, "required": required}


def _output(name: str, port_type: str = PORT_TYPE_FILE) -> dict:
    return {"name": name, "type": port_type}


# Task type definitions: id, label, inputs, outputs, supported backends, default config
TASK_TYPES = [
    {
        "id": "routing",
        "label": "Run routing (QAOA/RL)",
        "inputs": [],
        "outputs": [_output("routing_json")],
        "backends": [BACKEND_LOCAL, BACKEND_IBM_QPU, BACKEND_AWS_EKS],
        "default_config": {"routing_method": "qaoa", "fast": False, "backend": BACKEND_LOCAL},
        "compute_resource": COMPUTE_FDTD,
    },
    {
        "id": "inverse_design",
        "label": "Inverse design (phase profile)",
        "inputs": [_input("routing_json")],
        "outputs": [_output("inverse_json"), _output("npy_path")],
        "backends": [BACKEND_LOCAL, BACKEND_AWS_EKS],
        "default_config": {"model": "mlp", "device": "auto", "backend": BACKEND_LOCAL},
        "compute_resource": COMPUTE_FDTD,
    },
    {
        "id": "protocol_teleport",
        "label": "Run protocol (teleport)",
        "inputs": [],
        "outputs": [_output("result")],
        "backends": [BACKEND_LOCAL, BACKEND_IBM_QPU],
        "default_config": {"protocol": "teleport", "backend": BACKEND_LOCAL},
        # compute_resource: classical_sim when local, quantum_backend when ibm_qpu (resolved in dispatcher)
    },
    {
        "id": "protocol_bb84",
        "label": "QKD BB84",
        "inputs": [],
        "outputs": [_output("result")],
        "backends": [BACKEND_LOCAL],
        "default_config": {"n_bits": 64, "backend": BACKEND_LOCAL},
        "compute_resource": COMPUTE_CLASSICAL_SIM,
    },
    {
        "id": "protocol_e91",
        "label": "QKD E91",
        "inputs": [],
        "outputs": [_output("result")],
        "backends": [BACKEND_LOCAL],
        "default_config": {"n_trials": 500, "backend": BACKEND_LOCAL},
        "compute_resource": COMPUTE_CLASSICAL_SIM,
    },
    {
        "id": "quantum_illumination",
        "label": "Quantum illumination (DV)",
        "inputs": [],
        "outputs": [_output("result")],
        "backends": [BACKEND_LOCAL],
        "default_config": {"eta": 0.1, "backend": BACKEND_LOCAL},
        "compute_resource": COMPUTE_CLASSICAL_SIM,
    },
    {
        "id": "quantum_radar",
        "label": "Quantum radar (CV)",
        "inputs": [],
        "outputs": [_output("result")],
        "backends": [BACKEND_LOCAL],
        "default_config": {"eta": 0.1, "n_b": 10.0, "r": 0.5, "backend": BACKEND_LOCAL},
        "compute_resource": COMPUTE_CLASSICAL_SIM,
    },
    {
        "id": "heac_phases_to_geometry",
        "label": "HEaC phases → geometry",
        "inputs": [
            _input("routing_json"),
            _input("npy_path"),
            _input("heac_library", required=False),
        ],
        "outputs": [_output("manifest_path")],
        "backends": [BACKEND_LOCAL],
        "default_config": {"backend": BACKEND_LOCAL},
        "compute_resource": COMPUTE_FDTD,
    },
    {
        "id": "heac_library",
        "label": "HEaC meta-atom library",
        "inputs": [],
        "outputs": [_output("heac_library")],
        "backends": [BACKEND_LOCAL],
        "default_config": {"backend": BACKEND_LOCAL},
        "compute_resource": COMPUTE_FDTD,
    },
    {
        "id": "manifest_to_gds",
        "label": "Manifest → GDS",
        "inputs": [_input("manifest_path")],
        "outputs": [_output("gds_path")],
        "backends": [BACKEND_LOCAL],
        "default_config": {"backend": BACKEND_LOCAL},
        "compute_resource": COMPUTE_FDTD,
    },
    {
        "id": "thermal",
        "label": "Thermal report",
        "inputs": [_input("routing_json"), _input("npy_path")],
        "outputs": [_output("thermal_report")],
        "backends": [BACKEND_LOCAL],
        "default_config": {"backend": BACKEND_LOCAL},
        "compute_resource": COMPUTE_FDTD,
    },
]


def get_task_type(task_type_id: str) -> dict[str, Any] | None:
    """Return task type by id or None."""
    for t in TASK_TYPES:
        if t["id"] == task_type_id:
            return t
    return None


def list_task_types() -> list[dict[str, Any]]:
    """Return all task types (for palette and validation)."""
    return list(TASK_TYPES)


def get_supported_backends(task_type_id: str) -> list[str]:
    """Return list of backend ids supported for this task type."""
    t = get_task_type(task_type_id)
    return list(t["backends"]) if t else []


def get_required_inputs(task_type_id: str) -> list[str]:
    """Return names of required input ports."""
    t = get_task_type(task_type_id)
    if not t:
        return []
    return [inp["name"] for inp in t["inputs"] if inp.get("required", True)]


def get_output_names(task_type_id: str) -> list[str]:
    """Return names of output ports."""
    t = get_task_type(task_type_id)
    return [out["name"] for out in t["outputs"]] if t else []
