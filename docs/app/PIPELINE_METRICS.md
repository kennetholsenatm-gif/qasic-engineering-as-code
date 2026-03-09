# Pipeline Metrics and Bi-Weekly Review

This document defines **metrics to track** for pipeline execution and a **bi-weekly summary** template. It supports the TPM feedback loop: review pipeline success rates, latency, and failure reasons on a regular cadence.

No code changes are required by this doc; instrumentation can be added as a follow-up task.

---

## 1. Metrics to track

| Metric | Description | Source (current) |
|--------|-------------|------------------|
| **GDS generation success rate** | % of full-pipeline runs (with HEaC + GDS) that complete and produce a downloadable GDS. | Celery task result (success/failure); [storage.db](../../storage/db) pipeline runs if enabled; or API/task logs. |
| **Pipeline run latency** | Time from task enqueue to completion (p50, p95). | Celery result timestamps or task metadata; or application-level logging. |
| **Celery task failure rate** | % of pipeline (or circuit-to-ASIC) tasks that end in failure. | Celery result backend (Redis); worker logs. |
| **API latency** | Response time for `/api/run/pipeline` and `/api/run/pipeline/async`. | API server logs (e.g. uvicorn access log or middleware). |
| **Top failure reasons** | Count or list of most common errors (e.g. timeout, Qiskit matrix size, permission, missing dependency). | Task stderr/result; worker logs; optional aggregation script. |

---

## 2. Where data comes from

- **Celery / Redis:** Task ID, status (PENDING, SUCCESS, FAILURE), result or exception, timestamps. Use existing result backend; optional: export to a log or DB for querying.
- **API logs:** Request path, status code, duration. Add structured logging or use existing access logs.
- **storage.db pipeline runs:** If [record_pipeline_run](../../src/backend/main.py) and [update_pipeline_run](../../src/backend/tasks.py) are used with DB enabled, runs and status are stored; can query for success/failure and timestamps.

Instrumentation follow-up: centralize task outcome and duration (e.g. in DB or a small metrics endpoint) so bi-weekly reports do not require scraping raw logs.

---

## 3. Bi-weekly summary template

Use this template (or a short written summary) every two weeks.

| Field | Example |
|-------|--------|
| **Period** | e.g. 2026-03-01 to 2026-03-14 |
| **GDS success rate** | e.g. 85% (17/20 full-pipeline runs with GDS) |
| **Pipeline latency (p50 / p95)** | e.g. 8 min / 22 min |
| **Task failure rate** | e.g. 12% |
| **Top failure reasons** | e.g. 1) Timeout (5); 2) Qiskit qubit limit (3); 3) Permission (1) |
| **Action items** | e.g. Increase timeout for MEEP; document qubit limit in UI |
| **Next review** | e.g. 2026-03-28 |

Store summaries in a shared doc or in `docs/app/` (e.g. `PIPELINE_METRICS_SUMMARY_YYYY-MM-DD.md`) for traceability.

---

## 4. References

- [CELERY_TROUBLESHOOTING.md](CELERY_TROUBLESHOOTING.md) — Worker and queue diagnostics.
- [COMPUTE_COST_ASSESSMENT.md](COMPUTE_COST_ASSESSMENT.md) — Cost and margin (complementary to operational metrics).
- [PROGRAM_ACTION_ITEMS.md](PROGRAM_ACTION_ITEMS.md) — TPM feedback and bi-weekly cadence.
