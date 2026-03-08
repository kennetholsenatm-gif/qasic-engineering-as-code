# Data Persistence & Artifact Management

Optional production-style persistence is available via `config/storage_config.yaml` and environment variables. All features are **opt-in**: leave config empty or unset env vars to keep file-only behavior.

---

## 1. Artifact Store (MLflow)

**Purpose:** Track Bayesian/GNN runs, datasets (e.g. `.npz`, `.npy`), and model artifacts for reproducibility.

**Enable:** Set `MLFLOW_TRACKING_URI` (e.g. `http://localhost:5000` or `file:///path/to/mlruns`). Optionally configure `config/storage_config.yaml` → `artifact_store` (e.g. `experiment_name`).

**Usage:**
- **Datasets:** `engineering/meep_s_param_dataset.py` logs each generated dataset (e.g. `fdtd_dataset.npz`) to MLflow when the tracking URI is set (run name `meep_s_param_dataset`, params: `num_samples`, `config_size`, `output_size`, `use_meep`).
- **From code:** Use `storage.artifacts_mlflow.log_artifact_run(run_name, params=..., tags=..., artifacts=[...])` or `log_artifact_run_context(...)` for custom runs (e.g. GNN training, inverse design).

**Dependencies:** `mlflow>=2.9.0` (in root and app `requirements.txt`).

---

## 2. Time-Series DB (InfluxDB)

**Purpose:** Store telemetry and calibration data (T1/T2, gate fidelities, phase offsets) for dashboards and historical queries.

**Enable:** Set `INFLUX_URL` (e.g. `http://localhost:8086`). Optionally `INFLUX_TOKEN`, `INFLUX_ORG`, `INFLUX_BUCKET` (default bucket: `qasic-telemetry`). Config overrides in `config/storage_config.yaml` → `influx`.

**Usage:**
- **Calibration:** `engineering/calibration/run_calibration_cycle.py` writes each telemetry snapshot (from file or list) to InfluxDB when Influx is configured. Schema aligns with `engineering/calibration/telemetry_schema.py` (qubits, gate_fidelities, aggregate).
- **Query:** Use `engineering.calibration.telemetry_influx.query_telemetry(start_iso=..., stop_iso=..., limit=...)` to read back time-range queries.

**Dependencies:** `influxdb-client>=1.38.0`.

---

## 3. Relational DB (PostgreSQL)

**Purpose:** Track pipeline run state, hardware/config metadata, and latest result paths instead of relying only on flat JSON/YAML.

**Enable:** Set `DATABASE_URL` (e.g. `postgresql://user:pass@localhost:5432/qasic`). Table `pipeline_runs` is created automatically on first use.

**Schema (conceptual):**
- `pipeline_runs`: `id`, `output_base`, `status` (running | success | failed), `started_at`, `finished_at`, `config` (JSONB), `routing_path`, `inverse_path`, `task_id` (Celery), `error_message`.

**Usage:**
- **Sync pipeline:** `POST /api/run/pipeline` records a run at start and updates it on success/failure when `DATABASE_URL` is set.
- **Async pipeline:** `POST /api/run/pipeline/async` enqueues the task then records a run with `task_id`; the Celery worker updates the same row on completion.
- **Latest results:** `GET /api/results/latest` uses the most recent row from `pipeline_runs` (when DB is enabled) for `routing_path` and `inverse_path`, then loads JSON from those file paths. Falls back to config-based paths when DB is not configured.

**Dependencies:** `sqlalchemy>=2.0.0`, `psycopg2-binary>=2.9.0`.

---

## Summary

| Layer            | Env / config              | Use case                          |
|------------------|---------------------------|------------------------------------|
| **MLflow**       | `MLFLOW_TRACKING_URI`     | Datasets, GNN/inverse runs, reproducibility |
| **InfluxDB**     | `INFLUX_URL`, `INFLUX_*`  | Telemetry, calibration time-series |
| **PostgreSQL**   | `DATABASE_URL`            | Pipeline run state, latest result paths     |

All three are independent: you can enable any subset. File-based behavior remains the default when no persistence is configured.
