# Bayesian-Quantum Traffic Controller

Four-stage pipeline: **Telemetry (sFlow/NetFlow)** → **Bayesian inference** → **Qiskit QUBO optimizer** → **VyOS BGP actuator**.

## Setup

```bash
pip install -r requirements.txt
```

Configure `config/topology.yaml` (leafs, paths, VNIs) and `config/pipeline.yaml` (ports, intervals, dry_run).

## Run

```bash
python pipeline.py
```

- Start VyOS sFlow/NetFlow export to this host (ports 6343 and 2055 by default).
- Pipeline runs periodically (default 300 s); Bayesian stage uses the last 10 minutes of flows to predict bandwidth and Qiskit solves path selection; actuator applies BGP local-preference (dry-run by default).

## Layout

- `telemetry/` – UDP collectors and rolling buffer
- `bayesian/` – Features, model (sklearn or PyMC), inference
- `quantum/` – QUBO builder, QAOA solver, path → BGP mapping
- `actuator/` – VyOS client (pyvyos/vymgmt), BGP policy, apply
- `pipeline.py` – Main loop
- `config/` – topology.yaml, pipeline.yaml
