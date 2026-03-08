# Pipeline and Calibration Orchestration (Prefect DAG)

The metasurface pipeline and calibration cycle can be run as a **DAG** using [Prefect 2](https://docs.prefect.io/) so that:

- **Only failed nodes are retried** (e.g. MEEP FDTD fails after 10 hours → retry just the MEEP task).
- You can use the **Prefect UI** for runs, logs, and (optionally) distributed workers.

## Quick start

From repo root:

```bash
# Install Prefect
pip install -r requirements.txt

# Run pipeline with orchestrator (Prefect DAG, in-process retries)
python engineering/run_pipeline.py --use-orchestrator -o my_result --heac --thermal
```

Without `--use-orchestrator`, the same script runs the **original sequential pipeline** (no per-task retries).

## Layout

| Path | Purpose |
|------|---------|
| `orchestration/pipeline_params.py` | `PipelineParams` dataclass (mirrors CLI). |
| `orchestration/pipeline_tasks.py` | One function per step (routing, inverse, HEaC, GDS, DRC, LVS, DFT, thermal, MEEP, packaging, parasitic). |
| `orchestration/pipeline_flow.py` | Prefect flow `qasic-pipeline`: wraps tasks with `@task(retries=...)` and wires dependencies. |
| `orchestration/calibration_flow.py` | Prefect flow `qasic-calibration`: load telemetry → Influx (optional) → Bayesian update → write decoherence. |
| `engineering/run_pipeline.py` | CLI: add `--use-orchestrator` or `PREFECT_ORCHESTRATOR=1` to run the flow. |

## Running with a Prefect server

For a UI and run history:

```bash
prefect server start
# In another terminal, from repo root:
prefect flow run orchestration.pipeline_flow:pipeline_flow
```

To use **distributed workers**, start a worker process and point it at the server; then submit flow runs (see [Prefect workers](https://docs.prefect.io/latest/concepts/work-pools/)).

## See also

- [orchestration/README.md](../orchestration/README.md) – Task list, CLI options, calibration flow, retry settings.
