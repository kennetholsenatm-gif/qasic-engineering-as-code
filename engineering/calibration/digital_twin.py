"""
Digital twin state: current best-estimate decoherence rates per node and optional phase offsets.
Updated by Bayesian inference from telemetry; consumed by routing and simulation.
"""
from __future__ import annotations

from typing import Any

import numpy as np


class DigitalTwin:
    """
    Holds decoherence rates (per node) and optional phase offsets (per cell or per node).
    Can be initialized from file or from arrays; updated by calibration cycle.
    """

    def __init__(
        self,
        n_nodes: int = 3,
        decoherence_rates: np.ndarray | None = None,
        phase_offsets: np.ndarray | None = None,
    ):
        self.n_nodes = n_nodes
        self.decoherence_rates = (
            np.asarray(decoherence_rates, dtype=np.float64)
            if decoherence_rates is not None
            else np.ones(n_nodes, dtype=np.float64) * 0.1
        )
        if len(self.decoherence_rates) != n_nodes:
            self.decoherence_rates = np.resize(self.decoherence_rates, n_nodes)
        self.phase_offsets = (
            np.asarray(phase_offsets, dtype=np.float64)
            if phase_offsets is not None
            else None
        )

    def to_decoherence_json(self) -> dict[str, Any]:
        """Format for decoherence_rates.get_node_decoherence_rates_from_file()."""
        # gamma1, gamma2 from single rate: gamma1 = rate, gamma2 = rate/2
        nodes = []
        for r in self.decoherence_rates:
            nodes.append({"gamma1": float(r), "gamma2": float(r) * 0.5})
        return {"nodes": nodes, "source": "digital_twin"}

    def update_rates(self, new_rates: np.ndarray) -> None:
        """Update decoherence rates (e.g. from Bayesian posterior)."""
        new_rates = np.asarray(new_rates, dtype=np.float64)
        n = min(len(new_rates), self.n_nodes)
        self.decoherence_rates[:n] = new_rates[:n]

    def update_phase_offsets(self, offsets: np.ndarray) -> None:
        """Update phase offsets (optional)."""
        self.phase_offsets = np.asarray(offsets, dtype=np.float64)
