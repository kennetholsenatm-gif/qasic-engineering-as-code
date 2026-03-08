"""
Compute adapters for the hybrid dispatcher. Register adapters for local, IBM QPU, EKS.
"""
from __future__ import annotations

from src.backend.adapters.base import ComputeAdapter
from src.backend.adapters.local import LocalComputeAdapter
from src.backend.adapters.ibm import IBMQuantumAdapter
from src.backend.adapters.kubernetes import KubernetesJobAdapter

# Default registry order: first matching adapter wins
DEFAULT_ADAPTERS: list[ComputeAdapter] = [
    LocalComputeAdapter(),
    IBMQuantumAdapter(),
    KubernetesJobAdapter(),
]


def get_adapter_for(task_type: str, backend: str) -> ComputeAdapter | None:
    """Return the first adapter that supports (task_type, backend)."""
    for adapter in DEFAULT_ADAPTERS:
        if adapter.supports(task_type, backend):
            return adapter
    return None


__all__ = [
    "ComputeAdapter",
    "LocalComputeAdapter",
    "IBMQuantumAdapter",
    "KubernetesJobAdapter",
    "DEFAULT_ADAPTERS",
    "get_adapter_for",
]
