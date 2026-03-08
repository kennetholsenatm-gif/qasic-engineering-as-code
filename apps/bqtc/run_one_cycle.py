"""
Run a single BQTC pipeline cycle and print JSON result to stdout.
Used by the API when invoking from repo root with cwd=apps/bqtc.
Buffer has no live telemetry; inference uses whatever is in the buffer (e.g. zeros).
"""
import json
import sys
from pathlib import Path

# Run from apps/bqtc so data_plane, preproc, quantum_core, etc. resolve
from pipeline import load_config, run_one_cycle
from data_plane.service import create_telemetry_buffer

def main():
    pipeline_cfg, topology_cfg = load_config()
    telemetry_cfg = pipeline_cfg.get("telemetry", {})
    window_sec = telemetry_cfg.get("window_seconds", 600)
    buffer = create_telemetry_buffer(window_seconds=window_sec)
    results = run_one_cycle(buffer, pipeline_cfg, topology_cfg)
    out = [{"leaf": r.get("leaf"), "status": r.get("status"), "message": r.get("message", "")} for r in results]
    print(json.dumps(out))

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)
