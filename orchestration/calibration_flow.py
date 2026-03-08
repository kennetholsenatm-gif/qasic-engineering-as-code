"""
Prefect 2 flow: calibration cycle (load telemetry -> Bayesian update -> write decoherence).
Retriable as a single flow or split into tasks for future expansion.
"""
from __future__ import annotations

from prefect import flow, task


@task(name="load_telemetry", retries=2, retry_delay_seconds=5)
def load_telemetry_task(telemetry_input: str | list[dict]) -> list[dict]:
    """Load telemetry from file path or return list as-is."""
    if isinstance(telemetry_input, list):
        return telemetry_input
    from engineering.calibration.run_calibration_cycle import load_telemetry_from_file
    import os
    if not os.path.isfile(telemetry_input):
        raise FileNotFoundError(f"Telemetry file not found: {telemetry_input}")
    return load_telemetry_from_file(telemetry_input)


@task(name="write_influx", retries=1)
def write_telemetry_task(telemetry_list: list[dict]) -> bool:
    """Optionally write telemetry to InfluxDB."""
    try:
        from engineering.calibration.telemetry_influx import write_telemetry
        return write_telemetry(telemetry_list)
    except Exception:
        return False


@task(name="update_twin_and_write", retries=2, retry_delay_seconds=10)
def update_twin_and_write_task(
    telemetry_list: list[dict],
    output_decoherence_path: str,
    n_nodes: int = 3,
    prior_decoherence_file: str | None = None,
) -> str:
    """Run Bayesian update and write decoherence JSON."""
    from engineering.calibration.digital_twin import DigitalTwin
    from engineering.calibration.bayesian_update import update_decoherence_from_telemetry
    import json
    import os

    twin = None
    if prior_decoherence_file and os.path.isfile(prior_decoherence_file):
        with open(prior_decoherence_file, encoding="utf-8") as f:
            prior = json.load(f)
        nodes = prior.get("nodes", [])
        if nodes:
            rates = []
            for n in nodes:
                g1 = n.get("gamma1", 0.1)
                g2 = n.get("gamma2", 0.05)
                rates.append(float(g1) + float(g2) * 0.5)
            import numpy as np
            twin = DigitalTwin(n_nodes=len(rates), decoherence_rates=np.array(rates))

    if twin is None:
        twin = DigitalTwin(n_nodes=n_nodes)
    twin = update_decoherence_from_telemetry(telemetry_list, twin=twin, n_nodes=n_nodes)
    out = twin.to_decoherence_json()
    with open(output_decoherence_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    return output_decoherence_path


@flow(name="qasic-calibration", description="Telemetry -> digital twin -> decoherence file")
def calibration_flow(
    telemetry_input: str | list[dict],
    output_decoherence_path: str = "decoherence_from_calibration.json",
    n_nodes: int = 3,
    prior_decoherence_file: str | None = None,
) -> str:
    """
    Run one calibration cycle as a DAG: load telemetry, optionally write to Influx, update twin, write decoherence.
    """
    telemetry_list = load_telemetry_task(telemetry_input)
    write_telemetry_task(telemetry_list)  # best-effort
    return update_twin_and_write_task(
        telemetry_list,
        output_decoherence_path,
        n_nodes=n_nodes,
        prior_decoherence_file=prior_decoherence_file,
    )
