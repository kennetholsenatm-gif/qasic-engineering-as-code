"""
Time and flow aggregation for Bayesian inference.
Builds features from rolling window + clock for bandwidth prediction per VNI/path.
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np

from telemetry.models import FlowRecord


def aggregate_flows_by_vni(
    flows: List[FlowRecord],
    vnis: Optional[List[int]] = None,
    path_ids: Optional[List[str]] = None,
) -> Dict[Tuple[Optional[int], Optional[str]], float]:
    """
    Aggregate flow bytes by (vni, path). Path can be inferred from output_ifindex
    or left as None for aggregate per VNI. Returns (vni, path) -> bytes_per_second
    (rate over the time span of the flows).
    """
    if not flows:
        return {}
    times = [f.timestamp.timestamp() for f in flows]
    t_min, t_max = min(times), max(times)
    span_sec = max(t_max - t_min, 1.0)
    agg: Dict[Tuple[Optional[int], Optional[str]], float] = {}
    for f in flows:
        vni = f.vni if (vnis is None or f.vni in vnis) else None
        path = path_ids[f.output_ifindex] if path_ids and f.output_ifindex is not None else None
        key = (vni, path)
        agg[key] = agg.get(key, 0) + f.bytes_count
    # Convert to rate (bytes per second)
    for k in agg:
        agg[k] = agg[k] / span_sec
    return agg


def time_features(dt: Optional[datetime] = None) -> np.ndarray:
    """
    Time-of-day and optional calendar features for the model.
    Returns array: [hour_0_24, sin_hour, cos_hour, day_of_week_0_6].
    """
    dt = dt or datetime.utcnow()
    hour = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
    sin_h = np.sin(2 * np.pi * hour / 24.0)
    cos_h = np.cos(2 * np.pi * hour / 24.0)
    dow = dt.weekday()
    return np.array([hour / 24.0, sin_h, cos_h, dow / 7.0], dtype=np.float64)


def build_feature_matrix(
    flows: List[FlowRecord],
    vnis: List[int],
    path_ids: List[str],
    dt: Optional[datetime] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Build X (features) and y (target bytes/sec) for regression.
    Each row: time features + one-hot or index for vni and path.
    y: observed bytes per second for that (vni, path) in the window.
    """
    time_f = time_features(dt)
    agg = aggregate_flows_by_vni(flows, vnis=vnis, path_ids=None)
    # If we don't have path in flows, use single "aggregate" path per VNI
    rows_x: List[np.ndarray] = []
    rows_y: List[float] = []
    for vni in vnis:
        for path_id in path_ids:
            key = (vni, None)
            rate = agg.get(key, 0.0)
            # Also check (vni, path_id) if we had path info
            rate = agg.get((vni, path_id), rate)
            # Feature: time + vni index + path index (normalized)
            vni_idx = vnis.index(vni) / max(len(vnis), 1)
            path_idx = path_ids.index(path_id) / max(len(path_ids), 1)
            x = np.concatenate([time_f, np.array([vni_idx, path_idx])])
            rows_x.append(x)
            rows_y.append(rate)
    if not rows_x:
        # At least one row per (vni, path) with zero rate
        for vni in vnis:
            for path_id in path_ids:
                vni_idx = vnis.index(vni) / max(len(vnis), 1)
                path_idx = path_ids.index(path_id) / max(len(path_ids), 1)
                rows_x.append(np.concatenate([time_f, np.array([vni_idx, path_idx])]))
                rows_y.append(0.0)
    return np.array(rows_x), np.array(rows_y, dtype=np.float64)


def build_bandwidth_matrix_shape(vnis: List[int], path_ids: List[str]) -> Tuple[int, int]:
    """Return (n_vnis, n_paths) for the bandwidth matrix."""
    return len(vnis), len(path_ids)
