# Pulse-Level Control Synthesis

The **pulse** package compiles ASIC gate-level circuits to **pulse schedules** for microwave or optical control. This bridges the logical layer (`asic/gate_set.py`, `asic/circuit.py`) and state simulation (`state/`) to hardware control (OpenPulse, and optionally QICK for RFSoC).

## Data flow

1. **Input:** ASIC circuit — a list of ops (gate name, target qubits, optional parameter) from `asic.circuit` or from a JSON file.
2. **Backend config:** Number of qubits, sample time (`dt`), pulse durations and amplitudes (see `pulse/schedule_config_schema.json`).
3. **Output:** Either a **Qiskit OpenPulse** `Schedule` (when `qiskit.pulse` is available) or a **pseudo-schedule** dict (list of instructions with channel, t0, duration, gate) that can be serialized to JSON and consumed by other backends (e.g. QICK export).

## Gate-to-pulse mapping

| Gate | Pulse implementation |
|------|----------------------|
| H, X, Z | Single-qubit Gaussian (or parametrized) on `DriveChannel(q)` |
| Rx(angle) | Parametrized amplitude/duration on drive channel |
| CNOT(c,t) | Two-qubit sequence (e.g. cross-resonance style) on drive/control channels for c and t |

Topology is respected: only qubits and edges defined in the backend (or ASIC topology) receive pulses. The compiler does not add gates that violate the connectivity.

## Usage

### API

```python
from asic.circuit import protocol_teleport_ops
from pulse import compile_circuit_to_schedule

ops = protocol_teleport_ops()
config = {"n_qubits": 3, "dt": 1e-9}
schedule = compile_circuit_to_schedule(ops, config, topology=None)
# schedule is a qiskit.pulse.Schedule or a dict (pseudo_v1)
```

### CLI

From the repo root:

```bash
# Compile built-in teleport circuit to schedule.json (pseudo format if no qiskit.pulse)
python -m pulse --circuit teleport -o schedule.json

# Use a backend config file
python -m pulse --circuit teleport --config pulse/schedule_config_schema.json -o schedule.json

# Other built-in circuits: commitment, thief
python -m pulse --circuit commitment -o schedule.json
```

Circuit can also be a path to a JSON file containing an `ops` list: `[{"gate": "H", "targets": [0]}, ...]`.

### Backend config

- **n_qubits:** Number of qubits (default 3).
- **dt:** Sample time in seconds (default 1e-9).
- **duration_1q / duration_2q:** Samples per single- and two-qubit gate (OpenPulse).
- **samples_per_1q_gate / samples_per_2q_gate:** Used by pseudo-schedule when Qiskit Pulse is not installed.
- **amp:** Default pulse amplitude.
- **qubits:** Optional per-qubit calibration (frequency, scale).

## Optional: QICK export

A future backend can convert the same pseudo-schedule (or OpenPulse schedule) to QICK-compatible code or config for FPGA/RFSoC control. The pseudo-schedule format is chosen so that `instructions` (channel, t0, duration, gate, qubit/control/target) can be mapped to QICK waveform and timing without depending on Qiskit at runtime.

## Dependencies

- **Pseudo-schedule:** None beyond the repo (asic, state not required for pseudo_schedule only).
- **OpenPulse:** `qiskit` with pulse support (`pip install qiskit`).

## See also

- [QUANTUM_ASIC.md](QUANTUM_ASIC.md) — gate set and topology.
- [engineering/README.md](../engineering/README.md) — routing and inverse design pipeline.
