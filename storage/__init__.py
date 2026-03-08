"""
Optional data persistence: MLflow artifacts, InfluxDB telemetry, PostgreSQL pipeline runs.
Enable via config/storage_config.yaml or env: MLFLOW_TRACKING_URI, INFLUX_*, DATABASE_URL.
"""
from __future__ import annotations

from storage.artifacts_mlflow import log_artifact_run, log_artifact_run_context, is_enabled as mlflow_enabled
from storage.db import (
    get_engine,
    is_enabled as db_enabled,
    record_pipeline_run,
    update_pipeline_run,
    get_latest_pipeline_run,
)

__all__ = [
    "log_artifact_run",
    "log_artifact_run_context",
    "mlflow_enabled",
    "record_pipeline_run",
    "update_pipeline_run",
    "get_latest_pipeline_run",
    "get_engine",
    "db_enabled",
]
