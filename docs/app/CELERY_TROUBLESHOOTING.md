# Celery / "In queue" troubleshooting

If pipeline tasks stay **"In queue"** for a long time, either no worker is running, the worker is not connected to Redis, or the worker is stuck/crashed.

## 1. Is the Celery worker running?

**Docker Compose:**

```bash
cd /path/to/qasic-engineering-as-code
docker compose ps
```

Check that `celery-worker` is **Up**. If it is **Exit 1** or missing, the worker is not running.

- **Restart the worker:** `docker compose up -d celery-worker`
- **View worker logs:** `docker compose logs celery-worker --tail 100`

Look for:
- `celery@... ready` — worker connected and consuming.
- `ConnectionRefusedError`, `redis.exceptions.ConnectionError` — worker cannot reach Redis (wrong `CELERY_BROKER_URL` or Redis not running).
- Python tracebacks — task or import error; worker may be crashing on task receipt.

**Not using Docker (local dev):**

If you started the API with `uvicorn` but never started a worker, tasks will sit in the queue. Start a worker in a separate terminal:

```bash
CELERY_BROKER_URL=redis://localhost:6379/0 celery -A src.backend.celery_app worker -l info
```

(Ensure Redis is running locally and the URL matches what the API uses.)

## 2. Is Redis up and reachable?

**Docker:**

```bash
docker compose ps redis
docker compose exec redis redis-cli ping
```

Expected: `PONG`. If the exec fails, Redis is down or not in the same network.

**Queue length (tasks waiting):**

```bash
docker compose exec redis redis-cli LLEN celery
```

- `0` — queue empty; if the UI still shows "In queue", the task may already be with a worker (check worker logs) or the result key expired.
- `1` or more — that many tasks are waiting; if the worker is running and healthy, it should pick them up. If the number never goes down, the worker is not consuming (see step 1).

## 3. Insufficient workers?

With Docker Compose there is **one** `celery-worker` container (one process). It can run only **one task at a time** by default (`worker_prefetch_multiplier=1` in `src/backend/celery_app.py`). So:

- One long-running pipeline run blocks the next until it finishes.
- If the current task is slow or stuck, everything else stays "In queue".

**Options:**

- **Scale workers (Docker Compose):**  
  `docker compose up -d --scale celery-worker=2`  
  (or higher) to run two or more workers.
- **Check for a stuck task:**  
  Worker logs show which task is running. If one task runs for hours, others will wait.

## 4. Quick checklist

| Check | Command / action |
|-------|-------------------|
| Worker running? | `docker compose ps` → `celery-worker` Up |
| Worker logs | `docker compose logs celery-worker --tail 100` |
| Redis reachable? | `docker compose exec redis redis-cli ping` |
| Tasks waiting? | `docker compose exec redis redis-cli LLEN celery` |
| Restart worker | `docker compose restart celery-worker` |
| More workers | `docker compose up -d --scale celery-worker=2` |

If the worker is **Up** and logs show `ready` and no errors, but `LLEN celery` stays > 0 and never decreases, the worker may be stuck on a task (check logs for the running task and consider restarting the worker). If the worker keeps exiting, fix the error in the logs (e.g. missing env, Redis URL, or import/task error).

---

## 5. [Errno 13] Permission denied

This usually means the Celery worker (running as `appuser` in the container) tried to read or write a file/directory and was denied.

**Find the failing path:**

```bash
docker compose logs celery-worker --tail 200
```

Look for the full Python traceback; the last line often shows the path (e.g. `PermissionError: [Errno 13] Permission denied: '/app/src/core_compute/engineering/circuit_runs/...'`).

**Common causes:**

| Cause | Fix |
|-------|-----|
| Output dir not writable in image | Rebuild the image so `circuit_runs` is created and owned by `appuser`: `docker compose build --no-cache api` then `docker compose up -d celery-worker`. |
| Host volume mounted over `/app` | Don’t mount a read-only or root-owned host path over `/app`. The default compose does not mount the repo into api/celery-worker. |
| Windows + Docker file permissions | Rebuild without cache: `docker compose build --no-cache api`. If the host repo is on a permission-restricted drive, build from a directory the container user can write to. |
| Credentials/vault path | If `QASIC_CREDENTIALS_FILE` or app config points to a path outside `/app` or to a read-only location, change it to a path under `/app` (e.g. `storage/credentials.json`) or leave empty. |

**Quick fix:** Rebuild and restart so the image has writable dirs and correct ownership:

```bash
docker compose build --no-cache api
docker compose up -d celery-worker
```
