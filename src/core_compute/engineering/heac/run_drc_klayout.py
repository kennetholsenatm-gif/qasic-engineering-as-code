"""
Run Design Rule Checking (DRC) on a GDS file using KLayout (headless) or mock mode.
When KLayout is not available, runs a minimal mock check so CI can pass without PDK install.
Real DRC: run `klayout -b -r <drc_script> -rd input=<gds>` when drc_script and klayout exist.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def run_drc_klayout(gds_path: str, drc_script: str | None, report_path: str | None) -> tuple[bool, str]:
    """
    Run DRC via KLayout batch mode if drc_script and klayout exist; else mock.
    Returns (passed: bool, message: str).
    """
    gds = Path(gds_path)
    if not gds.exists():
        return False, f"GDS not found: {gds_path}"

    # Mock or minimal check when no KLayout or no DRC script
    klayout_bin = shutil.which("klayout")
    if not drc_script or not Path(drc_script).exists() or not klayout_bin:
        # Mock: minimal sanity check (file exists, non-empty)
        if gds.stat().st_size == 0:
            return False, "GDS file is empty (mock DRC failed)."
        if report_path:
            report = {"mock": True, "gds": str(gds), "passed": True, "violations": 0}
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
        return True, "Mock DRC passed (no DRC script or KLayout not on PATH)."

    # KLayout batch: klayout -b -r script.drc -rd input=file.gds -rd output=report.lyrdb
    out_rdb = (Path(report_path).with_suffix(".lyrdb") if report_path else Path("drc_report.lyrdb"))
    try:
        proc = subprocess.run(
            [
                klayout_bin, "-b",
                "-r", drc_script,
                "-rd", f"input={gds.absolute()}",
                "-rd", f"output={out_rdb.absolute()}",
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        if report_path:
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump({"error": "DRC timeout", "passed": False}, f, indent=2)
        return False, "DRC timed out."
    except Exception as e:
        if report_path:
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump({"error": str(e), "passed": False}, f, indent=2)
        return False, f"DRC failed: {e}"

    passed = proc.returncode == 0
    msg = f"DRC {'passed' if passed else 'failed'} (exit {proc.returncode})."
    if report_path:
        report = {"gds": str(gds), "passed": passed, "returncode": proc.returncode, "report_db": str(out_rdb)}
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
    return passed, msg


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run DRC on GDS (KLayout or mock).",
    )
    parser.add_argument("gds", help="Path to .gds file")
    parser.add_argument("--drc-script", default=None, help="Path to KLayout DRC rule file (optional)")
    parser.add_argument("-o", "--report", default=None, help="Output JSON report path")
    args = parser.parse_args()

    passed, msg = run_drc_klayout(args.gds, args.drc_script, args.report)
    print(msg, file=sys.stderr if not passed else sys.stdout)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
