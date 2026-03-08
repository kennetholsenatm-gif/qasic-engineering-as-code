"""
Celery app with Redis broker for async pipeline, MEEP sweeps, and GNN training.
Set CELERY_BROKER_URL (e.g. redis://localhost:6379/0) to enable async tasks.
"""
from __future__ import annotations

import os

broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
result_backend = os.environ.get("CELERY_RESULT_BACKEND", broker_url)

_celery_app = None


def get_celery_app():
    global _celery_app
    if _celery_app is None:
        from celery import Celery
        _celery_app = Celery(
            "qasic",
            broker=broker_url,
            backend=result_backend,
            include=["src.backend.tasks"],
        )
        _celery_app.conf.update(
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            timezone="UTC",
            enable_utc=True,
            task_track_started=True,
            task_time_limit=3600,
            worker_prefetch_multiplier=1,
        )
    return _celery_app
