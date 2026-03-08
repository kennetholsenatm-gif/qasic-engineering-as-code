"""
Compute adapter base: pluggable execution backends for the hybrid dispatcher.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class ComputeAdapter(ABC):
    """
    Abstract adapter for a compute backend (local, IBM QPU, EKS, etc.).
    Dispatcher resolves (task_type, backend) to an adapter and calls execute().
    """

    @abstractmethod
    def execute(
        self,
        task_type: str,
        config: dict[str, Any],
        inputs: dict[str, Any],
        work_dir: Path,
    ) -> tuple[dict[str, Any], str | None]:
        """
        Run the task. Returns (outputs dict, error_message or None).
        """
        ...

    def supports(self, task_type: str, backend: str) -> bool:
        """
        Return True if this adapter handles the given (task_type, backend).
        Override in subclasses; default returns False.
        """
        return False
