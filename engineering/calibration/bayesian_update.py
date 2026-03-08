"""
Bayesian update of decoherence rates from telemetry (T1/T2 per qubit).
Simple conjugate update: treat rate ~ 1/T2 as Gamma with prior; update from observed T2.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from .digital_twin import DigitalTwin
from .telemetry_schema import validate_telemetry


def telemetry_to_rates(telemetry: dict[str, Any], n_nodes: int) -> np.ndarray:
    """
    Convert telemetry qubits (T1_us, T2_us) to effective decoherence rates.
    rate ~ 1/T2 (us^-1) scaled to typical units; clip to avoid zeros.
    """
    rates = np.ones(n_nodes, dtype=np.float64) * 0.1
    qubits = telemetry.get("qubits", [])
    for i, q in enumerate(qubits):
        if i >= n_nodes:
            break
        if isinstance(q, dict):
            T2 = q.get("T2_us")
            T1 = q.get("T1_us")
            if T2 is not None and T2 > 0:
                rates[i] = 1.0 / float(T2)  # us^-1 as proxy
            elif T1 is not None and T1 > 0:
                rates[i] = 1.0 / float(T1)
    return np.clip(rates, 1e-4, 10.0)


def update_decoherence_from_telemetry(
    telemetry_list: list[dict[str, Any]],
    twin: DigitalTwin | None = None,
    n_nodes: int = 3,
    prior_scale: float = 1.0,
) -> DigitalTwin:
    """
    Update digital twin decoherence from a list of telemetry snapshots.
    Simple running average of telemetry_to_rates with optional prior (twin state).
    """
    if twin is None:
        twin = DigitalTwin(n_nodes=n_nodes)
    if not telemetry_list:
        return twin
    rates_list = []
    for t in telemetry_list:
        valid, _ = validate_telemetry(t)
        if valid:
            rates_list.append(telemetry_to_rates(t, n_nodes))
    if not rates_list:
        return twin
    stack = np.array(rates_list)
    posterior_mean = np.mean(stack, axis=0)
    if prior_scale > 0 and twin.decoherence_rates is not None:
        # Blend with prior
        prior = twin.decoherence_rates[: len(posterior_mean)]
        posterior_mean = (1.0 - 1.0 / (1.0 + prior_scale)) * prior + (1.0 / (1.0 + prior_scale)) * posterior_mean
    n = min(len(posterior_mean), twin.n_nodes)
    twin.update_rates(posterior_mean[:n])
    return twin
