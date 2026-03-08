"""
Optional PostgreSQL persistence for pipeline runs and latest results.
Set DATABASE_URL (e.g. postgresql://user:pass@localhost:5432/qasic) to enable.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

_engine = None


def _database_url() -> str | None:
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        return url
    try:
        from config import get_storage_config
        return get_storage_config().database.url or None
    except Exception:
        return None


def is_enabled() -> bool:
    return _database_url() is not None


def get_engine():
    """Get SQLAlchemy engine; create pipeline_runs table if needed. Returns None if DATABASE_URL not set."""
    global _engine
    url = _database_url()
    if not url:
        return None
    if _engine is not None:
        return _engine
    try:
        from sqlalchemy import create_engine, text
        _engine = create_engine(url, pool_pre_ping=True)
        with _engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS pipeline_runs (
                    id SERIAL PRIMARY KEY,
                    output_base VARCHAR(256) NOT NULL,
                    status VARCHAR(32) NOT NULL,
                    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    finished_at TIMESTAMP WITH TIME ZONE,
                    config JSONB,
                    routing_path TEXT,
                    inverse_path TEXT,
                    task_id VARCHAR(256),
                    error_message TEXT
                )
            """))
            conn.commit()
        return _engine
    except Exception:
        _engine = None
        return None


def record_pipeline_run(
    output_base: str,
    config: dict[str, Any] | None = None,
    task_id: str | None = None,
) -> int | None:
    """Insert a new pipeline run (status=running). Returns run id or None."""
    engine = get_engine()
    if engine is None:
        return None
    try:
        from sqlalchemy import text
        import json
        with engine.connect() as conn:
            r = conn.execute(
                text(
                    "INSERT INTO pipeline_runs (output_base, status, started_at, config, task_id) "
                    "VALUES (:ob, 'running', :now, CAST(:config AS jsonb), :tid) RETURNING id"
                ),
                {
                    "ob": output_base,
                    "now": datetime.now(timezone.utc),
                    "config": json.dumps(config) if config else None,
                    "tid": task_id,
                },
            )
            row = r.fetchone()
            conn.commit()
            return row[0] if row else None
    except Exception:
        return None


def update_pipeline_run(
    run_id: int | None = None,
    task_id: str | None = None,
    status: str = "success",
    routing_path: str | None = None,
    inverse_path: str | None = None,
    error_message: str | None = None,
) -> bool:
    """Update pipeline run by run_id or task_id. Sets finished_at and status."""
    engine = get_engine()
    if engine is None:
        return False
    try:
        from sqlalchemy import text
        now = datetime.now(timezone.utc)
        if run_id is not None:
            with engine.connect() as conn:
                conn.execute(
                    text("""
                        UPDATE pipeline_runs
                        SET status = :st, finished_at = :now, routing_path = COALESCE(:rp, routing_path),
                            inverse_path = COALESCE(:ip, inverse_path), error_message = :err
                        WHERE id = :id
                    """),
                    {
                        "st": status,
                        "now": now,
                        "rp": routing_path,
                        "ip": inverse_path,
                        "err": error_message,
                        "id": run_id,
                    },
                )
                conn.commit()
        elif task_id:
            with engine.connect() as conn:
                conn.execute(
                    text("""
                        UPDATE pipeline_runs
                        SET status = :st, finished_at = :now, routing_path = COALESCE(:rp, routing_path),
                            inverse_path = COALESCE(:ip, inverse_path), error_message = :err
                        WHERE task_id = :tid
                    """),
                    {
                        "st": status,
                        "now": now,
                        "rp": routing_path,
                        "ip": inverse_path,
                        "err": error_message,
                        "tid": task_id,
                    },
                )
                conn.commit()
        else:
            return False
        return True
    except Exception:
        return False


def get_latest_pipeline_run(output_base: str | None = None) -> dict[str, Any] | None:
    """Return the most recent pipeline run (optionally for given output_base) with paths and summary."""
    engine = get_engine()
    if engine is None:
        return None
    try:
        from sqlalchemy import text
        if output_base:
            q = "SELECT id, output_base, status, started_at, finished_at, config, routing_path, inverse_path FROM pipeline_runs WHERE output_base = :ob ORDER BY started_at DESC LIMIT 1"
            params = {"ob": output_base}
        else:
            q = "SELECT id, output_base, status, started_at, finished_at, config, routing_path, inverse_path FROM pipeline_runs ORDER BY started_at DESC LIMIT 1"
            params = {}
        with engine.connect() as conn:
            r = conn.execute(text(q), params)
            row = r.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "output_base": row[1],
            "status": row[2],
            "started_at": row[3].isoformat() if row[3] else None,
            "finished_at": row[4].isoformat() if row[4] else None,
            "config": row[5],
            "routing_path": row[6],
            "inverse_path": row[7],
        }
    except Exception:
        return None
