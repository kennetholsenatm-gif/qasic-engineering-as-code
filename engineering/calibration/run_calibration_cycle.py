"""
Run one calibration cycle: read telemetry, update digital twin, write decoherence file.
Can be driven by live telemetry (REST/file) or synthetic data for testing.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from .digital_twin import DigitalTwin
from .bayesian_update import update_decoherence_from_telemetry
from .telemetry_schema import validate_telemetry


def load_telemetry_from_file(path: str) -> list[dict]:
    """Load one or more telemetry snapshots from JSON file."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return [data]


def run_calibration_cycle(
    telemetry_input: str | list[dict],
    output_decoherence_path: str,
    n_nodes: int = 3,
    prior_decoherence_file: str | None = None,
) -> int:
    """
    Run one cycle: load telemetry, update twin, write decoherence JSON.
    telemetry_input: path to JSON file or list of telemetry dicts.
    Returns 0 on success.
    """
    if isinstance(telemetry_input, str):
        if not os.path.isfile(telemetry_input):
            print(f"Telemetry file not found: {telemetry_input}", file=sys.stderr)
            return 1
        telemetry_list = load_telemetry_from_file(telemetry_input)
    else:
        telemetry_list = telemetry_input

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
    print(f"Wrote {output_decoherence_path} ({len(out['nodes'])} nodes)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run calibration cycle: telemetry -> digital twin -> decoherence file.",
    )
    parser.add_argument("telemetry", help="Path to telemetry JSON (single snapshot or list)")
    parser.add_argument("-o", "--output", default="decoherence_from_calibration.json", help="Output decoherence JSON")
    parser.add_argument("--n-nodes", type=int, default=3, help="Number of nodes (qubits)")
    parser.add_argument("--prior", default=None, help="Path to prior decoherence file (optional)")
    args = parser.parse_args()

    return run_calibration_cycle(
        args.telemetry,
        args.output,
        n_nodes=args.n_nodes,
        prior_decoherence_file=args.prior,
    )


if __name__ == "__main__":
    sys.exit(main())
