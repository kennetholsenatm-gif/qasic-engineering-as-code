"""
Sweep stale DAG runs: mark as failed runs with status='running' and no recent heartbeat.

Run as a cron job or Celery beat task every 1–2 minutes. Example:
  * Cron: */2 * * * * cd /path/to/repo && python -m src.backend.sweep_stale_runs
  * Celery: app.conf.beat_schedule = {"sweep-stale-runs": {"task": "qasic.sweep_stale_dag_runs", "schedule": 120}}
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def main() -> int:
    """Run sweep and print count of runs marked failed. Exit 0."""
    from storage.db import sweep_stale_dag_runs, is_enabled
    if not is_enabled():
        print("Database not configured; skip sweep.")
        return 0
    interval = 60  # seconds
    n = sweep_stale_dag_runs(interval_seconds=interval)
    if n > 0:
        print(f"Marked {n} stale run(s) as failed (no heartbeat in {interval}s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
