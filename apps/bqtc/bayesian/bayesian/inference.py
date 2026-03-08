"""
Orchestration: load telemetry from rolling buffer, featurize, fit/predict, emit bandwidth matrix.
"""

from datetime import datetime
from typing import List, Optional

import numpy as np

from telemetry.collector import RollingBuffer
from telemetry.models import FlowRecord

from .features import build_feature_matrix
from .model import predict_bandwidth_matrix


def run_inference(
    buffer: RollingBuffer,
    vnis: List[int],
    path_ids: List[str],
    dt: Optional[datetime] = None,
    backend: str = "sklearn",
    model_type: str = "bayesian_ridge",
) -> np.ndarray:
    """
    Run Bayesian inference: get flows from buffer, build features, predict bandwidth matrix.
    Returns B[vni_idx][path_idx] in bytes per second.
    """
    dt = dt or datetime.utcnow()
    flows: List[FlowRecord] = buffer.get_flows()
    if not flows and not vnis:
        return np.zeros((1, max(len(path_ids), 1)))
    if not vnis:
        # Infer VNIs from flows
        seen_vnis = {f.vni for f in flows if f.vni is not None}
        vnis = sorted(seen_vnis) if seen_vnis else [0]
    if not path_ids:
        path_ids = ["path0"]
    X, y = build_feature_matrix(flows, vnis, path_ids, dt=dt)
    return predict_bandwidth_matrix(
        X, y, vnis, path_ids, dt=dt, backend=backend, model_type=model_type
    )
