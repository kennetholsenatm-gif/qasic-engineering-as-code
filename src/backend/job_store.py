"""
IBM protocol job store: Redis-backed for multi-worker, in-memory fallback.
Allows WebSocket /status to work regardless of which worker handled the submit.
"""
from __future__ import annotations

import json
import os
from typing import Any

# In-memory fallback when Redis not used (single-worker only)
_memory_store: dict[str, dict[str, Any]] = {}

REDIS_KEY_PREFIX = "qasic:ibm_job:"
TTL_SECONDS = 86400 * 2  # 2 days


def _redis_client():
    url = os.environ.get("CELERY_BROKER_URL", "").strip() or os.environ.get("REDIS_URL", "").strip()
    if not url or not url.startswith("redis"):
        return None
    try:
        import redis
        return redis.from_url(url, decode_responses=True)
    except Exception:
        return None


def set_job(job_id: str, *, ibm_job_id: str | None = None, backend: str, protocol: str, job: Any = None) -> None:
    """Store job metadata. Use ibm_job_id for Redis (any worker can poll); use job for in-memory (single worker)."""
    client = _redis_client()
    if client:
        payload = {"ibm_job_id": ibm_job_id, "backend": backend, "protocol": protocol}
        key = REDIS_KEY_PREFIX + job_id
        try:
            client.setex(key, TTL_SECONDS, json.dumps(payload))
        except Exception:
            pass
        return
    if job is not None:
        _memory_store[job_id] = {"job": job, "backend": backend, "protocol": protocol}
    else:
        _memory_store[job_id] = {"ibm_job_id": ibm_job_id, "backend": backend, "protocol": protocol}


def get_job(job_id: str) -> dict[str, Any] | None:
    """Return stored entry: {job?, ibm_job_id?, backend, protocol}. job only in memory; ibm_job_id in Redis."""
    client = _redis_client()
    if client:
        key = REDIS_KEY_PREFIX + job_id
        try:
            raw = client.get(key)
            if raw:
                return json.loads(raw)
        except Exception:
            pass
        return None
    return _memory_store.get(job_id)
