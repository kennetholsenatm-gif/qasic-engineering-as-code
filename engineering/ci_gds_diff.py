"""
Produce a short diff report between current pipeline output and CI baseline.
Used in Hardware CI to post GDS/layout change summary (e.g. cell count, phase stats).
Compares geometry manifest and optionally phase array; no GDS binary diff (avoid large files).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def load_manifest(path: str) -> dict | None:
    if not path or not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def manifest_summary(data: dict) -> dict:
    """Compact summary for diff: num_cells, shape, pitch."""
    return {
        "num_cells": data.get("num_cells", 0),
        "shape": data.get("shape", []),
        "pitch_um": data.get("pitch_um"),
    }


def phase_summary(npy_path: str) -> dict | None:
    """Summary of phase array if .npy exists."""
    if not npy_path or not os.path.isfile(npy_path):
        return None
    try:
        import numpy as np
        arr = np.load(npy_path)
        arr = np.asarray(arr, dtype=np.float64).ravel()
        return {
            "size": int(arr.size),
            "mean": float(np.mean(arr)),
            "std": float(np.std(arr)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
        }
    except Exception:
        return None


def run_diff(
    manifest_path: str,
    baseline_dir: str | None,
    phases_path: str | None,
) -> tuple[str, int]:
    """
    Compare current manifest (and optional phases) to baseline. Return (report_text, exit_code).
    Exit 0 if no baseline or diff is informational only; non-zero only on hard failure.
    """
    current = load_manifest(manifest_path)
    if not current:
        return "No current manifest found.", 1
    current_summary = manifest_summary(current)
    report_lines = ["## Hardware CI diff (manifest)", "", f"Current: {current_summary}"]

    baseline_manifest = None
    if baseline_dir and os.path.isdir(baseline_dir):
        baseline_path = os.path.join(baseline_dir, "ci_result_geometry_manifest.json")
        if os.path.isfile(baseline_path):
            baseline_manifest = load_manifest(baseline_path)
    if baseline_manifest:
        base_summary = manifest_summary(baseline_manifest)
        report_lines.append("")
        report_lines.append(f"Baseline: {base_summary}")
        if current_summary.get("num_cells") != base_summary.get("num_cells"):
            report_lines.append("")
            report_lines.append(f"**Cell count changed:** {base_summary.get('num_cells')} -> {current_summary.get('num_cells')}")
    else:
        report_lines.append("")
        report_lines.append("(No baseline found; store manifest in engineering/ci_baseline/ for diff.)")

    if phases_path and os.path.isfile(phases_path):
        ps = phase_summary(phases_path)
        if ps:
            report_lines.append("")
            report_lines.append("Phase array summary: " + json.dumps(ps, indent=0))
            base_phases = None
            if baseline_dir and os.path.isdir(baseline_dir):
                bp = os.path.join(baseline_dir, "ci_result_inverse_phases.npy")
                if os.path.isfile(bp):
                    base_phases = phase_summary(bp)
            if base_phases:
                report_lines.append("Baseline phases: " + json.dumps(base_phases, indent=0))
                if abs((ps.get("mean") or 0) - (base_phases.get("mean") or 0)) > 0.01:
                    report_lines.append("(Phase mean shifted vs baseline.)")

    report_lines.append("")
    return "\n".join(report_lines), 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Diff current pipeline manifest/phases vs CI baseline.",
    )
    parser.add_argument("manifest", help="Path to geometry_manifest.json (current run)")
    parser.add_argument("--baseline-dir", default=None, help="Baseline directory (e.g. engineering/ci_baseline)")
    parser.add_argument("--phases", default=None, help="Path to phases .npy for phase summary diff")
    parser.add_argument("-o", "--output", default=None, help="Write report to file")
    args = parser.parse_args()

    baseline = args.baseline_dir or os.path.join(os.path.dirname(__file__), "ci_baseline")
    report, code = run_diff(args.manifest, baseline, args.phases)
    print(report)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
    return code


if __name__ == "__main__":
    sys.exit(main())
