# Calibration and Digital Twin

The **digital twin** mode uses telemetry (e.g. per-qubit T1/T2, gate fidelities) to update the virtual "decoherence rates" and optionally phase offsets used by the EaC pipeline. This closes the loop between live device data and design/simulation so the same framework supports both design-time and operational calibration.

## Data flow

1. **Telemetry:** Quantum device exposes metrics (T1/T2 per qubit, gate fidelities, phase drift). Ingest from file, REST, or a stub (e.g. JSON/CSV) for testing.
2. **Digital twin state:** Current best-estimate decoherence rates per node and optional phase offsets. Stored in memory and/or persisted as `decoherence_from_calibration.json`.
3. **Bayesian update:** From historical telemetry, compute posterior over decoherence rates (simple running average or conjugate update). Optionally phase corrections from drift metrics.
4. **Output:** Write decoherence file in the format expected by `engineering/decoherence_rates.py` so that routing (`--decoherence-file`) and simulation can use layout- and calibration-aware rates.

## Telemetry schema

Minimal schema (see `engineering/calibration/telemetry_schema.py`):

- **qubits:** List of `{ "index", "T1_us", "T2_us", "phase_offset_rad" }`.
- **gate_fidelities:** Optional list of `{ "gate", "qubits", "fidelity" }`.
- **aggregate:** Optional `mean_T1_us`, `mean_T2_us`, `drift_score`.

T1/T2 are used to derive effective decoherence rates (e.g. rate ∝ 1/T2) for the twin.

## Usage

### Calibration cycle (CLI)

From repo root:

```bash
# Run the calibration script (path relative to repo root)
python engineering/calibration/run_calibration_cycle.py telemetry.json -o decoherence_from_calibration.json

# With prior (previous decoherence file) and 3 nodes
python engineering/calibration/run_calibration_cycle.py telemetry.json -o out.json --prior current_decoherence.json --n-nodes 3
```

If `engineering` is on `PYTHONPATH`, you can also run:

```bash
python -m engineering.calibration.run_calibration_cycle telemetry.json -o decoherence_from_calibration.json
```

### Using calibration output in routing

Pass the output file to routing so that logical→physical mapping accounts for updated decoherence:

```bash
python engineering/routing_qubo_qaoa.py --decoherence-file engineering/decoherence_from_calibration.json -o routing.json
```

### API

```python
from engineering.calibration import DigitalTwin, update_decoherence_from_telemetry, run_calibration_cycle

# From telemetry list
telemetry_list = [{"qubits": [{"index": 0, "T1_us": 50, "T2_us": 30}, ...]}]
twin = update_decoherence_from_telemetry(telemetry_list, n_nodes=3)
with open("decoherence.json", "w") as f:
    json.dump(twin.to_decoherence_json(), f, indent=2)
```

## Optional: BQTC integration

The BQTC app (`apps/bqtc/`) already runs telemetry → Bayesian inference → QUBO → actuator for **network** path selection. To prove EaC for both network and quantum, you can add a "quantum calibration" mode that:

- Reads the same or a separate telemetry stream (quantum device metrics).
- Runs `run_calibration_cycle` and writes `decoherence_from_calibration.json` to a shared config/state directory.
- Optionally re-runs routing with `--decoherence-file` to suggest a new logical→physical mapping, or document that in production this drives recommended re-calibration or automatic tuning.

This is not required for the digital twin to be useful; routing and simulation can consume the calibration output independently.

## See also

- [engineering/decoherence_rates.py](../engineering/decoherence_rates.py) — `get_node_decoherence_rates_from_file()`
- [THERMAL_AND_PARASITICS.md](THERMAL_AND_PARASITICS.md) — layout-derived decoherence (parasitic extraction)
- [apps/bqtc/](../apps/bqtc/) — Bayesian inference and telemetry pipeline for network control
