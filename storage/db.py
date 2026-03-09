"""
Optional PostgreSQL persistence for pipeline runs and latest results.
Set DATABASE_URL (e.g. postgresql://user:pass@localhost:5432/qasic) to enable.
Project-based workspace: projects table is parent; pipeline_runs belong to a project (or default).
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
    """Get SQLAlchemy engine; create projects and pipeline_runs tables if needed. Returns None if DATABASE_URL not set."""
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
                CREATE TABLE IF NOT EXISTS projects (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(256) NOT NULL UNIQUE,
                    description TEXT,
                    config JSONB DEFAULT '{}',
                    mlflow_experiment_id VARCHAR(256),
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc')
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS pipeline_runs (
                    id SERIAL PRIMARY KEY,
                    project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
                    output_base VARCHAR(256) NOT NULL,
                    status VARCHAR(32) NOT NULL,
                    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    finished_at TIMESTAMP WITH TIME ZONE,
                    config JSONB,
                    routing_path TEXT,
                    inverse_path TEXT,
                    gds_path TEXT,
                    task_id VARCHAR(256),
                    error_message TEXT
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS dag_definitions (
                    id SERIAL PRIMARY KEY,
                    project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
                    name VARCHAR(256) NOT NULL,
                    nodes JSONB NOT NULL DEFAULT '[]',
                    edges JSONB NOT NULL DEFAULT '[]',
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc')
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS dag_runs (
                    id SERIAL PRIMARY KEY,
                    dag_id INTEGER REFERENCES dag_definitions(id) ON DELETE SET NULL,
                    status VARCHAR(32) NOT NULL,
                    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    finished_at TIMESTAMP WITH TIME ZONE,
                    celery_task_id VARCHAR(256),
                    error_message TEXT,
                    nodes_snapshot JSONB,
                    edges_snapshot JSONB
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS dag_run_nodes (
                    id SERIAL PRIMARY KEY,
                    run_id INTEGER NOT NULL REFERENCES dag_runs(id) ON DELETE CASCADE,
                    node_id VARCHAR(128) NOT NULL,
                    status VARCHAR(32) NOT NULL,
                    started_at TIMESTAMP WITH TIME ZONE,
                    finished_at TIMESTAMP WITH TIME ZONE,
                    outputs JSONB,
                    error_message TEXT,
                    UNIQUE(run_id, node_id)
                )
            """))
            conn.commit()
            # Add project_id and gds_path if table already existed (migration-friendly)
            try:
                conn.execute(text("ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL"))
                conn.execute(text("ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS gds_path TEXT"))
                conn.execute(text("ALTER TABLE dag_runs ADD COLUMN IF NOT EXISTS last_heartbeat TIMESTAMP WITH TIME ZONE"))
                conn.commit()
            except Exception:
                pass
        return _engine
    except Exception:
        _engine = None
        return None


def record_pipeline_run(
    output_base: str,
    config: dict[str, Any] | None = None,
    task_id: str | None = None,
    project_id: int | None = None,
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
                    "INSERT INTO pipeline_runs (output_base, status, started_at, config, task_id, project_id) "
                    "VALUES (:ob, 'running', :now, CAST(:config AS jsonb), :tid, :pid) RETURNING id"
                ),
                {
                    "ob": output_base,
                    "now": datetime.now(timezone.utc),
                    "config": json.dumps(config) if config else None,
                    "tid": task_id,
                    "pid": project_id,
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
    gds_path: str | None = None,
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
                            inverse_path = COALESCE(:ip, inverse_path), gds_path = COALESCE(:gp, gds_path), error_message = :err
                        WHERE id = :id
                    """),
                    {
                        "st": status,
                        "now": now,
                        "rp": routing_path,
                        "ip": inverse_path,
                        "gp": gds_path,
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
                            inverse_path = COALESCE(:ip, inverse_path), gds_path = COALESCE(:gp, gds_path), error_message = :err
                        WHERE task_id = :tid
                    """),
                    {
                        "st": status,
                        "now": now,
                        "rp": routing_path,
                        "ip": inverse_path,
                        "gp": gds_path,
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


def _row_to_run(row: tuple) -> dict[str, Any]:
    """Map pipeline_runs row to dict (handles 8-column legacy or 12-column with project_id, gds_path)."""
    n = len(row)
    out = {
        "id": row[0],
        "output_base": row[1],
        "status": row[2],
        "started_at": row[3].isoformat() if row[3] else None,
        "finished_at": row[4].isoformat() if row[4] else None,
        "config": row[5],
        "routing_path": row[6],
        "inverse_path": row[7],
    }
    if n >= 10:
        out["task_id"] = row[8]
        out["error_message"] = row[9]
    if n >= 11:
        out["gds_path"] = row[10]
    if n >= 12:
        out["project_id"] = row[11]
    return out


def get_latest_pipeline_run(output_base: str | None = None, project_id: int | None = None) -> dict[str, Any] | None:
    """Return the most recent pipeline run (optionally for given output_base or project_id) with paths and summary."""
    engine = get_engine()
    if engine is None:
        return None
    try:
        from sqlalchemy import text
        q = """SELECT id, output_base, status, started_at, finished_at, config, routing_path, inverse_path, task_id, error_message, gds_path, project_id
               FROM pipeline_runs"""
        params = {}
        clauses = []
        if output_base:
            clauses.append("output_base = :ob")
            params["ob"] = output_base
        if project_id is not None:
            clauses.append("(project_id = :pid OR (project_id IS NULL AND :pid IS NULL))")
            params["pid"] = project_id
        if clauses:
            q += " WHERE " + " AND ".join(clauses)
        q += " ORDER BY started_at DESC LIMIT 1"
        with engine.connect() as conn:
            r = conn.execute(text(q), params)
            row = r.fetchone()
        if not row:
            return None
        return _row_to_run(row)
    except Exception:
        try:
            q = "SELECT id, output_base, status, started_at, finished_at, config, routing_path, inverse_path FROM pipeline_runs ORDER BY started_at DESC LIMIT 1"
            with engine.connect() as conn:
                r = conn.execute(text(q))
                row = r.fetchone()
            if not row:
                return None
            return {f: row[i] for i, f in enumerate(["id", "output_base", "status", "started_at", "finished_at", "config", "routing_path", "inverse_path"])}
        except Exception:
            return None


# --- Project CRUD ---

def create_project(name: str, description: str | None = None, config: dict[str, Any] | None = None) -> int | None:
    """Create a project. Returns project id or None."""
    engine = get_engine()
    if engine is None:
        return None
    try:
        from sqlalchemy import text
        import json
        with engine.connect() as conn:
            r = conn.execute(
                text("""
                    INSERT INTO projects (name, description, config, updated_at)
                    VALUES (:name, :desc, CAST(:config AS jsonb), :now) RETURNING id
                """),
                {
                    "name": name,
                    "desc": description or "",
                    "config": json.dumps(config or {}),
                    "now": datetime.now(timezone.utc),
                },
            )
            row = r.fetchone()
            conn.commit()
            return row[0] if row else None
    except Exception:
        return None


def get_project(project_id: int) -> dict[str, Any] | None:
    """Get a single project by id."""
    engine = get_engine()
    if engine is None:
        return None
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            r = conn.execute(
                text("SELECT id, name, description, config, mlflow_experiment_id, created_at, updated_at FROM projects WHERE id = :id"),
                {"id": project_id},
            )
            row = r.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "name": row[1],
            "description": row[2] or "",
            "config": row[3] or {},
            "mlflow_experiment_id": row[4],
            "created_at": row[5].isoformat() if row[5] else None,
            "updated_at": row[6].isoformat() if row[6] else None,
        }
    except Exception:
        return None


def list_projects() -> list[dict[str, Any]]:
    """List all projects."""
    engine = get_engine()
    if engine is None:
        return []
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            r = conn.execute(text("""
                SELECT p.id, p.name, p.description, p.config, p.mlflow_experiment_id, p.created_at, p.updated_at,
                       (SELECT COUNT(*) FROM pipeline_runs pr WHERE pr.project_id = p.id AND pr.status = 'running') AS active_runs
                FROM projects p
                ORDER BY p.updated_at DESC
            """))
            rows = r.fetchall()
        return [
            {
                "id": row[0],
                "name": row[1],
                "description": row[2] or "",
                "config": row[3] or {},
                "mlflow_experiment_id": row[4],
                "created_at": row[5].isoformat() if row[5] else None,
                "updated_at": row[6].isoformat() if row[6] else None,
                "active_runs": row[7] if len(row) > 7 else 0,
            }
            for row in rows
        ]
    except Exception:
        try:
            with engine.connect() as conn:
                r = conn.execute(text("SELECT id, name, description, config, mlflow_experiment_id, created_at, updated_at FROM projects ORDER BY updated_at DESC"))
                rows = r.fetchall()
            return [
                {
                    "id": row[0],
                    "name": row[1],
                    "description": row[2] or "",
                    "config": row[3] or {},
                    "mlflow_experiment_id": row[4],
                    "created_at": row[5].isoformat() if row[5] else None,
                    "updated_at": row[6].isoformat() if row[6] else None,
                    "active_runs": 0,
                }
                for row in rows
            ]
        except Exception:
            return []


def update_project(project_id: int, name: str | None = None, description: str | None = None) -> bool:
    """Update project name and/or description."""
    engine = get_engine()
    if engine is None:
        return False
    try:
        from sqlalchemy import text
        updates = ["updated_at = :now"]
        params = {"id": project_id, "now": datetime.now(timezone.utc)}
        if name is not None:
            updates.append("name = :name")
            params["name"] = name
        if description is not None:
            updates.append("description = :description")
            params["description"] = description
        if len(params) <= 2:
            return True
        with engine.connect() as conn:
            conn.execute(text(f"UPDATE projects SET {', '.join(updates)} WHERE id = :id"), params)
            conn.commit()
        return True
    except Exception:
        return False


def delete_project(project_id: int) -> bool:
    """Delete a project. Pipeline runs referencing it will have project_id set to NULL (ON DELETE SET NULL)."""
    engine = get_engine()
    if engine is None:
        return False
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM projects WHERE id = :id"), {"id": project_id})
            conn.commit()
        return True
    except Exception:
        return False


def update_project_mlflow_experiment(project_id: int, mlflow_experiment_id: str) -> bool:
    """Set MLflow experiment id for a project."""
    engine = get_engine()
    if engine is None:
        return False
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(
                text("UPDATE projects SET mlflow_experiment_id = :eid, updated_at = :now WHERE id = :id"),
                {"eid": mlflow_experiment_id, "now": datetime.now(timezone.utc), "id": project_id},
            )
            conn.commit()
        return True
    except Exception:
        return False


def get_pipeline_run(run_id: int) -> dict[str, Any] | None:
    """Return a single pipeline run by id, or None."""
    engine = get_engine()
    if engine is None:
        return None
    try:
        from sqlalchemy import text
        q = """SELECT id, output_base, status, started_at, finished_at, config, routing_path, inverse_path, task_id, error_message, gds_path, project_id
               FROM pipeline_runs WHERE id = :rid"""
        with engine.connect() as conn:
            r = conn.execute(text(q), {"rid": run_id})
            row = r.fetchone()
        if not row:
            return None
        return _row_to_run(row)
    except Exception:
        return None


def list_pipeline_runs(project_id: int | None = None, limit: int = 50) -> list[dict[str, Any]]:
    """List pipeline runs, optionally filtered by project_id. Most recent first."""
    engine = get_engine()
    if engine is None:
        return []
    try:
        from sqlalchemy import text
        q = """SELECT id, output_base, status, started_at, finished_at, config, routing_path, inverse_path, task_id, error_message, gds_path, project_id
               FROM pipeline_runs"""
        params = {"limit": limit}
        if project_id is not None:
            q += " WHERE project_id = :pid"
            params["pid"] = project_id
        q += " ORDER BY started_at DESC LIMIT :limit"
        with engine.connect() as conn:
            r = conn.execute(text(q), params)
            rows = r.fetchall()
        return [_row_to_run(row) for row in rows]
    except Exception:
        try:
            q = "SELECT id, output_base, status, started_at, finished_at, config, routing_path, inverse_path FROM pipeline_runs ORDER BY started_at DESC LIMIT :limit"
            with engine.connect() as conn:
                r = conn.execute(text(q), {"limit": limit})
                rows = r.fetchall()
            return [{f: row[i] for i, f in enumerate(["id", "output_base", "status", "started_at", "finished_at", "config", "routing_path", "inverse_path"])} for row in rows]
        except Exception:
            return []


# --- DAG definitions and runs ---

def create_dag(name: str, nodes: list, edges: list, project_id: int | None = None) -> int | None:
    """Create a DAG definition. Returns dag id or None."""
    engine = get_engine()
    if engine is None:
        return None
    try:
        from sqlalchemy import text
        import json
        now = datetime.now(timezone.utc)
        with engine.connect() as conn:
            r = conn.execute(
                text("""
                    INSERT INTO dag_definitions (name, project_id, nodes, edges, created_at, updated_at)
                    VALUES (:name, :pid, CAST(:nodes AS jsonb), CAST(:edges AS jsonb), :now, :now) RETURNING id
                """),
                {"name": name, "pid": project_id, "nodes": json.dumps(nodes), "edges": json.dumps(edges), "now": now},
            )
            row = r.fetchone()
            conn.commit()
            return row[0] if row else None
    except Exception:
        return None


def get_dag(dag_id: int) -> dict[str, Any] | None:
    """Get a DAG definition by id."""
    engine = get_engine()
    if engine is None:
        return None
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            r = conn.execute(
                text("SELECT id, project_id, name, nodes, edges, created_at, updated_at FROM dag_definitions WHERE id = :id"),
                {"id": dag_id},
            )
            row = r.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "project_id": row[1],
            "name": row[2],
            "nodes": row[3] if row[3] is not None else [],
            "edges": row[4] if row[4] is not None else [],
            "created_at": row[5].isoformat() if row[5] else None,
            "updated_at": row[6].isoformat() if row[6] else None,
        }
    except Exception:
        return None


def list_dags(project_id: int | None = None, limit: int = 100) -> list[dict[str, Any]]:
    """List DAG definitions, optionally by project_id."""
    engine = get_engine()
    if engine is None:
        return []
    try:
        from sqlalchemy import text
        q = "SELECT id, project_id, name, nodes, edges, created_at, updated_at FROM dag_definitions"
        params = {"limit": limit}
        if project_id is not None:
            q += " WHERE project_id = :pid"
            params["pid"] = project_id
        q += " ORDER BY updated_at DESC LIMIT :limit"
        with engine.connect() as conn:
            r = conn.execute(text(q), params)
            rows = r.fetchall()
        return [
            {
                "id": row[0],
                "project_id": row[1],
                "name": row[2],
                "nodes": row[3] if row[3] is not None else [],
                "edges": row[4] if row[4] is not None else [],
                "created_at": row[5].isoformat() if row[5] else None,
                "updated_at": row[6].isoformat() if row[6] else None,
            }
            for row in rows
        ]
    except Exception:
        return []


def update_dag(dag_id: int, name: str | None = None, nodes: list | None = None, edges: list | None = None) -> bool:
    """Update a DAG definition. Pass only fields to update."""
    engine = get_engine()
    if engine is None:
        return False
    try:
        from sqlalchemy import text
        import json
        now = datetime.now(timezone.utc)
        updates = ["updated_at = :now"]
        params = {"id": dag_id, "now": now}
        if name is not None:
            updates.append("name = :name")
            params["name"] = name
        if nodes is not None:
            updates.append("nodes = CAST(:nodes AS jsonb)")
            params["nodes"] = json.dumps(nodes)
        if edges is not None:
            updates.append("edges = CAST(:edges AS jsonb)")
            params["edges"] = json.dumps(edges)
        with engine.connect() as conn:
            conn.execute(text(f"UPDATE dag_definitions SET {', '.join(updates)} WHERE id = :id"), params)
            conn.commit()
        return True
    except Exception:
        return False


def create_dag_run(dag_id: int | None, status: str, nodes_snapshot: list, edges_snapshot: list, celery_task_id: str | None = None) -> int | None:
    """Create a DAG run record. Returns run id or None."""
    engine = get_engine()
    if engine is None:
        return None
    try:
        from sqlalchemy import text
        import json
        now = datetime.now(timezone.utc)
        with engine.connect() as conn:
            r = conn.execute(
                text("""
                    INSERT INTO dag_runs (dag_id, status, started_at, nodes_snapshot, edges_snapshot, celery_task_id)
                    VALUES (:dag_id, :status, :now, CAST(:nodes AS jsonb), CAST(:edges AS jsonb), :tid) RETURNING id
                """),
                {"dag_id": dag_id, "status": status, "now": now, "nodes": json.dumps(nodes_snapshot), "edges": json.dumps(edges_snapshot), "tid": celery_task_id},
            )
            row = r.fetchone()
            conn.commit()
            return row[0] if row else None
    except Exception:
        return None


def get_dag_run(run_id: int) -> dict[str, Any] | None:
    """Get a DAG run by id with node statuses."""
    engine = get_engine()
    if engine is None:
        return None
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            r = conn.execute(
                text("SELECT id, dag_id, status, started_at, finished_at, celery_task_id, error_message, nodes_snapshot, edges_snapshot FROM dag_runs WHERE id = :id"),
                {"id": run_id},
            )
            row = r.fetchone()
        if not row:
            return None
        with engine.connect() as conn:
            r2 = conn.execute(
                text("SELECT node_id, status, started_at, finished_at, outputs, error_message FROM dag_run_nodes WHERE run_id = :rid ORDER BY id"),
                {"rid": run_id},
            )
            node_rows = r2.fetchall()
        node_statuses = [
            {"node_id": nr[0], "status": nr[1], "started_at": nr[2].isoformat() if nr[2] else None, "finished_at": nr[3].isoformat() if nr[3] else None, "outputs": nr[4], "error_message": nr[5]}
            for nr in node_rows
        ]
        return {
            "id": row[0],
            "dag_id": row[1],
            "status": row[2],
            "started_at": row[3].isoformat() if row[3] else None,
            "finished_at": row[4].isoformat() if row[4] else None,
            "celery_task_id": row[5],
            "error_message": row[6],
            "nodes_snapshot": row[7],
            "edges_snapshot": row[8],
            "nodes": node_statuses,
        }
    except Exception:
        return None


def update_dag_run(run_id: int, status: str | None = None, finished_at: datetime | None = None, error_message: str | None = None, celery_task_id: str | None = None, last_heartbeat: datetime | None = None) -> bool:
    """Update DAG run status and/or last_heartbeat."""
    engine = get_engine()
    if engine is None:
        return False
    try:
        from sqlalchemy import text
        params = {"id": run_id}
        updates = []
        if status is not None:
            updates.append("status = :status")
            params["status"] = status
        if finished_at is not None:
            updates.append("finished_at = :finished_at")
            params["finished_at"] = finished_at
        if error_message is not None:
            updates.append("error_message = :error_message")
            params["error_message"] = error_message
        if celery_task_id is not None:
            updates.append("celery_task_id = :celery_task_id")
            params["celery_task_id"] = celery_task_id
        if last_heartbeat is not None:
            updates.append("last_heartbeat = :last_heartbeat")
            params["last_heartbeat"] = last_heartbeat
        if not updates:
            return True
        with engine.connect() as conn:
            conn.execute(text(f"UPDATE dag_runs SET {', '.join(updates)} WHERE id = :id"), params)
            conn.commit()
        return True
    except Exception:
        return False


def update_dag_run_heartbeat(run_id: int) -> bool:
    """Set last_heartbeat to now for the given run (worker liveness)."""
    return update_dag_run(run_id, last_heartbeat=datetime.now(timezone.utc))


def sweep_stale_dag_runs(interval_seconds: int = 60) -> int:
    """
    Mark runs as failed where status='running' and last_heartbeat is older than interval_seconds.
    Returns the number of runs updated. Run as cron or Celery beat task.
    """
    engine = get_engine()
    if engine is None:
        return 0
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            r = conn.execute(
                text("""
                    UPDATE dag_runs
                    SET status = 'failed', error_message = 'Run timed out (no heartbeat)'
                    WHERE status = 'running'
                    AND (last_heartbeat IS NULL OR last_heartbeat < NOW() - INTERVAL '1 second' * :interval)
                    RETURNING id
                """),
                {"interval": interval_seconds},
            )
            ids = [row[0] for row in r.fetchall()]
            conn.commit()
        return len(ids)
    except Exception:
        return 0


def upsert_dag_run_node(run_id: int, node_id: str, status: str, started_at: datetime | None = None, finished_at: datetime | None = None, outputs: dict | None = None, error_message: str | None = None) -> bool:
    """Insert or update a node run record."""
    engine = get_engine()
    if engine is None:
        return False
    try:
        from sqlalchemy import text
        import json
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO dag_run_nodes (run_id, node_id, status, started_at, finished_at, outputs, error_message)
                    VALUES (:run_id, :node_id, :status, :started_at, :finished_at, CAST(:outputs AS jsonb), :err)
                    ON CONFLICT (run_id, node_id) DO UPDATE SET
                    status = EXCLUDED.status, started_at = COALESCE(EXCLUDED.started_at, dag_run_nodes.started_at),
                    finished_at = EXCLUDED.finished_at, outputs = COALESCE(EXCLUDED.outputs, dag_run_nodes.outputs), error_message = EXCLUDED.error_message
                """),
                {
                    "run_id": run_id,
                    "node_id": node_id,
                    "status": status,
                    "started_at": started_at,
                    "finished_at": finished_at,
                    "outputs": json.dumps(outputs) if outputs else None,
                    "err": error_message,
                },
            )
            conn.commit()
        return True
    except Exception:
        return False


def list_dag_runs(dag_id: int | None = None, limit: int = 50) -> list[dict[str, Any]]:
    """List DAG runs, optionally for one DAG."""
    engine = get_engine()
    if engine is None:
        return []
    try:
        from sqlalchemy import text
        q = "SELECT id, dag_id, status, started_at, finished_at, celery_task_id FROM dag_runs"
        params = {"limit": limit}
        if dag_id is not None:
            q += " WHERE dag_id = :dag_id"
            params["dag_id"] = dag_id
        q += " ORDER BY started_at DESC LIMIT :limit"
        with engine.connect() as conn:
            r = conn.execute(text(q), params)
            rows = r.fetchall()
        return [
            {"id": row[0], "dag_id": row[1], "status": row[2], "started_at": row[3].isoformat() if row[3] else None, "finished_at": row[4].isoformat() if row[4] else None, "celery_task_id": row[5]}
            for row in rows
        ]
    except Exception:
        return []
