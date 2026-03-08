"""
Optional MLflow artifact logging for datasets and model runs.
Set MLFLOW_TRACKING_URI (and optionally config/storage_config.yaml) to enable.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def _tracking_uri() -> str | None:
    uri = os.environ.get("MLFLOW_TRACKING_URI", "").strip()
    if uri:
        return uri
    try:
        from config import get_storage_config
        cfg = get_storage_config()
        return cfg.artifact_store.tracking_uri or None
    except Exception:
        return None


def _experiment_name() -> str:
    try:
        from config import get_storage_config
        return get_storage_config().artifact_store.experiment_name or "qasic-engineering"
    except Exception:
        return "qasic-engineering"


def is_enabled() -> bool:
    return _tracking_uri() is not None


def get_or_create_experiment(experiment_name: str) -> str | None:
    """
    Get or create an MLflow experiment by name. Returns experiment_id if successful.
    Used for project-based workspace: one experiment per project.
    """
    uri = _tracking_uri()
    if not uri:
        return None
    try:
        import mlflow
        mlflow.set_tracking_uri(uri)
        exp = mlflow.get_experiment_by_name(experiment_name)
        if exp is not None:
            return exp.experiment_id
        return mlflow.create_experiment(experiment_name)
    except Exception:
        return None


def log_artifact_run(
    run_name: str,
    params: dict[str, Any] | None = None,
    tags: dict[str, str] | None = None,
    artifacts: list[str | Path] | None = None,
    artifact_dir: str | Path | None = None,
    experiment_id: str | None = None,
    experiment_name: str | None = None,
) -> str | None:
    """
    Start an MLflow run, log params/tags and optional artifact files/dir, end run.
    If experiment_id or experiment_name (for get_or_create_experiment) is set, use that experiment;
    otherwise use default _experiment_name().
    Returns run_id if successful, None if MLflow not configured or on error.
    """
    uri = _tracking_uri()
    if not uri:
        return None
    try:
        import mlflow
        mlflow.set_tracking_uri(uri)
        if experiment_id:
            mlflow.set_experiment(experiment_id=experiment_id)
        elif experiment_name:
            eid = get_or_create_experiment(experiment_name)
            if eid:
                mlflow.set_experiment(experiment_id=eid)
            else:
                mlflow.set_experiment(_experiment_name())
        else:
            mlflow.set_experiment(_experiment_name())
        params = params or {}
        tags = tags or {}
        run_id = None
        with mlflow.start_run(run_name=run_name) as run:
            run_id = run.info.run_id
            for k, v in params.items():
                mlflow.log_param(k, str(v))
            for k, v in tags.items():
                mlflow.log_param(f"tag.{k}", v)
            if artifacts:
                for path in artifacts:
                    p = Path(path)
                    if p.is_file():
                        mlflow.log_artifact(str(p))
            if artifact_dir:
                d = Path(artifact_dir)
                if d.is_dir():
                    mlflow.log_artifacts(str(d))
        return run_id
    except Exception:
        return None


def log_artifact_run_context(run_name: str, params: dict[str, Any] | None = None, tags: dict[str, str] | None = None):
    """
    Context manager that starts an MLflow run; callers can log_artifact() inside.
    Use when you need to log multiple artifacts or log after computing something.
    """
    uri = _tracking_uri()
    if not uri:
        yield None
        return
    try:
        import mlflow
        mlflow.set_tracking_uri(uri)
        mlflow.set_experiment(_experiment_name())
        with mlflow.start_run(run_name=run_name):
            for k, v in (params or {}).items():
                mlflow.log_param(k, str(v))
            for k, v in (tags or {}).items():
                mlflow.log_param(f"tag.{k}", v)
            yield mlflow.active_run()
    except Exception:
        yield None
