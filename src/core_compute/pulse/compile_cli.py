"""
CLI: compile ASIC circuit to pulse schedule and optionally write schedule.json.
Usage: python -m pulse.compile_cli --circuit teleport --config config.json -o schedule.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_circuit_ops(spec: str) -> list:
    """Load circuit ops from 'teleport'|'commitment'|'thief' or path to JSON."""
    if spec.lower() == "teleport":
        from src.core_compute.asic.circuit import protocol_teleport_ops
        return protocol_teleport_ops()
    if spec.lower() == "commitment":
        from src.core_compute.asic.circuit import protocol_commitment_ops
        return protocol_commitment_ops()
    if spec.lower() == "thief":
        from src.core_compute.asic.circuit import protocol_thief_ops
        return protocol_thief_ops()
    path = Path(spec)
    if path.exists():
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        from dataclasses import dataclass
        @dataclass
        class Op:
            gate: str
            targets: list
            param: Any = None
        lst = data if isinstance(data, list) else data.get("ops", data.get("circuit", []))
        return [Op(gate=o["gate"], targets=o["targets"], param=o.get("param")) for o in lst]
    raise FileNotFoundError(f"Circuit spec not found: {spec}")


def load_config(path: str | None) -> dict:
    if not path or not Path(path).exists():
        return {"n_qubits": 3, "dt": 1e-9}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compile ASIC circuit to pulse schedule (OpenPulse or pseudo).",
    )
    parser.add_argument(
        "--circuit", "-c",
        default="teleport",
        help="Circuit: teleport, commitment, thief, or path to JSON with ops list.",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to backend config JSON (n_qubits, dt, durations, etc.).",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Write schedule to JSON (pseudo format) or leave empty for stdout.",
    )
    parser.add_argument(
        "--backend",
        default="default",
        choices=("default", "qick", "zurich"),
        help="Output backend: default (pseudo/OpenPulse), qick (QICK), zurich (Zurich Instruments).",
    )
    args = parser.parse_args()

    try:
        ops = load_circuit_ops(args.circuit)
    except Exception as e:
        print(f"Failed to load circuit: {e}", file=sys.stderr)
        return 1
    config = load_config(args.config)

    # For QICK/Zurich we need a dict schedule; use pseudo when backend is not default
    if args.backend in ("qick", "zurich"):
        try:
            from src.core_compute.pulse.pseudo_schedule import build_pseudo_schedule
            schedule = build_pseudo_schedule(ops, config)
        except Exception as e:
            print(f"Pseudo schedule failed: {e}", file=sys.stderr)
            return 1
        if args.backend == "qick":
            from src.core_compute.pulse.qick_export import write_qick_config
            out_path = args.output or "schedule_qick.json"
            write_qick_config(schedule, out_path, config)
            print(f"Wrote {out_path} (QICK format)")
        else:
            from src.core_compute.pulse.zurich_export import write_zurich_config
            out_path = args.output or "schedule_zurich.json"
            write_zurich_config(schedule, out_path, config)
            print(f"Wrote {out_path} (Zurich format)")
        return 0

    try:
        from src.core_compute.pulse.compiler import compile_circuit_to_schedule
        schedule = compile_circuit_to_schedule(ops, config, topology=None)
    except Exception as e:
        print(f"Compilation failed: {e}", file=sys.stderr)
        return 1

    # Serialize: if already dict (pseudo), use it; else Qiskit Schedule -> summary
    if isinstance(schedule, dict):
        out = schedule
    else:
        out = {
            "version": "openpulse_summary",
            "n_qubits": config.get("n_qubits", 3),
            "num_instructions": len(schedule.instructions),
            "duration": getattr(schedule, "duration", None),
        }

    text = json.dumps(out, indent=2)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
