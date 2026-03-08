# DAG Orchestration (Prefect 2)

Pipeline and calibration runs are available as **Prefect 2** flows so you can:

- **Retry only failed tasks** (e.g. if MEEP FDTD fails after 10 hours, retry just that node).
- Run with a **Prefect server** for a UI, scheduling, and distributed workers.

## Pipeline DAG

The metasurface pipeline is implemented as flow `qasic-pipeline` with tasks:

| Task | Retries | Depends on |
|------|---------|------------|
| routing | 2 | — |
| superscreen | 1 | routing |
| inverse_design | 2 | routing |
| heac_library | 2 | — (if --heac) |
| heac_phases_to_geometry | 2 | routing, inverse (npy), heac_library |
| manifest_to_gds | 2 | manifest |
| drc | 1 | gds |
| lvs | 1 | manifest, gds, routing |
| dft | 1 | manifest, gds |
| thermal | 1 | routing, npy |
| meep_verify | 1 | manifest |
| packaging | 1 | manifest |
| parasitic | 1 | manifest, routing |

## Run via orchestrator

### Option 1: CLI flag (same process)

From **repo root**:

```bash
python engineering/run_pipeline.py --use-orchestrator -o my_result --heac --thermal
```

Or set the env and use the script as usual:

```bash
export PREFECT_ORCHESTRATOR=1
python engineering/run_pipeline.py -o my_result
```

### Option 2: Prefect CLI (with server)

Start a Prefect server (optional) for a UI and history:

```bash
prefect server start
# In another terminal:
prefect worker start --pool default-agent-pool   # optional: remote workers
```

Run the flow from repo root:

```bash
cd /path/to/qasic-engineering-as-code
prefect flow run orchestration.pipeline_flow:pipeline_flow
```

With parameters (e.g. output base, heac) you can pass a JSON file or env; for programmatic runs use the Python API (see below).

### Option 3: Python API

From repo root:

```python
from orchestration import pipeline_flow, PipelineParams

params = PipelineParams(
    output_base="pipeline_result",
    fast=True,
    heac=True,
    thermal=True,
)
result = pipeline_flow(params)  # runs in-process with retries
```

## Calibration flow

Run a single calibration cycle as a DAG (load telemetry → optional Influx write → Bayesian update → write decoherence):

```bash
prefect flow run orchestration.calibration_flow:calibration_flow \
  --param telemetry_input=engineering/ci_baseline/ci_synthetic_telemetry.json \
  --param output_decoherence_path=engineering/ci_decoherence_from_calibration.json \
  --param n_nodes=3
```

Or from Python:

```python
from orchestration.calibration_flow import calibration_flow

path = calibration_flow(
    telemetry_input="engineering/ci_baseline/ci_synthetic_telemetry.json",
    output_decoherence_path="engineering/ci_decoherence_from_calibration.json",
    n_nodes=3,
)
```

## Sequential fallback

If Prefect is not installed or you do not pass `--use-orchestrator` / `PREFECT_ORCHESTRATOR`, `run_pipeline.py` runs the **original sequential script** (no per-task retries). So CI and one-off runs keep working without Prefect.

## Requirements

- `prefect>=2.14.0` (in repo root `requirements.txt`).
- Run pipeline/orchestration from **repo root** so `orchestration` and `engineering` resolve.

## Retry behavior

- Each task has `retries=1` or `2` and `retry_delay_seconds` (10–60). On failure, only that task is retried; upstream tasks are not re-run.
- For long-running steps (e.g. MEEP), increase `retry_delay_seconds` or configure retries in the flow/task decorators in `orchestration/pipeline_flow.py` and `orchestration/calibration_flow.py`.
