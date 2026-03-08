"""
Process variation (Monte Carlo) sweeps: perturb manifest dimensions, re-run parasitic/superconducting
extraction, aggregate L/C or qubit-frequency proxy for yield estimation.
Ref: NEXT_STEPS_ROADMAP.md §1.3 Process Variation (Monte Carlo) Sweeps.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path
from typing import Any

import numpy as np


def load_manifest(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_manifest(manifest: dict[str, Any], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def perturb_manifest(
    manifest: dict[str, Any],
    dimension_delta_um: float = 0.0,
    dimension_std_um: float = 0.02,
    pitch_std_um: float = 0.0,
    rng: np.random.Generator | None = None,
) -> dict[str, Any]:
    """Return a copy of manifest with dimensions perturbed. If dimension_std_um > 0, add Gaussian noise per cell."""
    rng = rng or np.random.default_rng()
    out = json.loads(json.dumps(manifest))
    pitch = out.get("pitch_um", 1.0)
    if pitch_std_um > 0:
        out["pitch_um"] = float(pitch + rng.normal(0, pitch_std_um))
    cells = out.get("cells", [])
    for c in cells:
        d = float(c.get("dimension", 0.5))
        if dimension_std_um > 0:
            d = d + rng.normal(0, dimension_std_um)
        d = d + dimension_delta_um
        c["dimension"] = max(0.01, round(d, 6))
    return out


def run_parasitic_extraction(manifest_path: str, routing_path: str | None, script_dir: str, repo_root: str) -> dict[str, Any] | None:
    """Run parasitic_extraction.py; return parsed JSON or None on failure."""
    import subprocess
    out_path = str(Path(manifest_path).parent / "_parasitic_tmp.json")
    cmd = [sys.executable, os.path.join(script_dir, "parasitic_extraction.py"), manifest_path, "-o", out_path]
    if routing_path and os.path.isfile(routing_path):
        cmd += ["--routing", routing_path]
    rc = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, timeout=60)
    if rc.returncode != 0 or not os.path.isfile(out_path):
        return None
    with open(out_path, encoding="utf-8") as f:
        data = json.load(f)
    try:
        os.remove(out_path)
    except OSError:
        pass
    return data


def run_superconducting_extraction(manifest_path: str, routing_path: str | None, script_dir: str, repo_root: str) -> dict[str, Any] | None:
    """Run superconducting_extraction.py; return parsed JSON or None on failure."""
    import subprocess
    out_path = str(Path(manifest_path).with_name(Path(manifest_path).stem + "_kinetic_tmp.json"))
    cmd = [sys.executable, os.path.join(script_dir, "superconducting_extraction.py"), manifest_path, "-o", out_path]
    if routing_path and os.path.isfile(routing_path):
        cmd += ["--routing", routing_path]
    rc = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, timeout=60)
    if rc.returncode != 0 or not os.path.isfile(out_path):
        return None
    with open(out_path, encoding="utf-8") as f:
        data = json.load(f)
    try:
        os.remove(out_path)
    except OSError:
        pass
    return data


def metric_from_parasitic(data: dict[str, Any]) -> float:
    """Single scalar metric from parasitic output (e.g. mean gamma1 over nodes)."""
    nodes = data.get("nodes", [])
    if not nodes:
        return 0.0
    return float(np.mean([n.get("gamma1", 0.1) for n in nodes]))


def metric_from_superconducting(data: dict[str, Any]) -> float:
    """Single scalar metric from superconducting output (e.g. mean L_kinetic_nH)."""
    nodes = data.get("nodes", [])
    if not nodes:
        return 0.0
    return float(np.mean([n.get("L_kinetic_nH", 0.0) for n in nodes]))


def run_sweep(
    nominal_manifest_path: str,
    routing_path: str | None,
    n_samples: int,
    dimension_std_um: float = 0.02,
    pitch_std_um: float = 0.0,
    seed: int = 42,
    run_superconducting: bool = True,
    script_dir: str | None = None,
    repo_root: str | None = None,
) -> dict[str, Any]:
    """
    Generate N manifest variants, run parasitic (and optionally superconducting) extraction per variant,
    return stats: mean, std, min, max of metric, and optional yield_at_spec (fraction below a threshold).
    """
    script_dir = script_dir or os.path.dirname(os.path.abspath(__file__))
    repo_root = repo_root or os.path.dirname(script_dir)
    nominal = load_manifest(nominal_manifest_path)
    base_dir = str(Path(nominal_manifest_path).parent)
    rng = np.random.default_rng(seed)
    metrics_parasitic: list[float] = []
    metrics_super: list[float] = []
    for i in range(n_samples):
        variant = perturb_manifest(
            nominal,
            dimension_std_um=dimension_std_um,
            pitch_std_um=pitch_std_um,
            rng=rng,
        )
        variant_path = os.path.join(base_dir, f"_variant_{i}.json")
        save_manifest(variant, variant_path)
        try:
            p_data = run_parasitic_extraction(variant_path, routing_path, script_dir, repo_root)
            if p_data is not None:
                metrics_parasitic.append(metric_from_parasitic(p_data))
            if run_superconducting:
                s_data = run_superconducting_extraction(variant_path, routing_path, script_dir, repo_root)
                if s_data is not None:
                    metrics_super.append(metric_from_superconducting(s_data))
        finally:
            try:
                os.remove(variant_path)
            except OSError:
                pass

    def stats(arr: list[float]) -> dict[str, float]:
        if not arr:
            return {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0, "count": 0}
        a = np.array(arr)
        return {
            "mean": float(np.mean(a)),
            "std": float(np.std(a)),
            "min": float(np.min(a)),
            "max": float(np.max(a)),
            "count": len(arr),
        }

    result: dict[str, Any] = {
        "source": "process_variation_sweep",
        "nominal_manifest": nominal_manifest_path,
        "n_samples": n_samples,
        "seed": seed,
        "dimension_std_um": dimension_std_um,
        "pitch_std_um": pitch_std_um,
        "parasitic_metric": stats(metrics_parasitic),
        "superconducting_metric": stats(metrics_super) if run_superconducting else None,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Process variation (Monte Carlo) sweep: perturb manifest, run extraction, aggregate stats.",
    )
    parser.add_argument("manifest", help="Path to nominal geometry_manifest.json")
    parser.add_argument("-n", "--samples", type=int, default=10, help="Number of variants")
    parser.add_argument("--routing", default=None, help="Path to routing.json (optional)")
    parser.add_argument("--dimension-std", type=float, default=0.02, dest="dimension_std", help="Std dev for dimension perturbation (um)")
    parser.add_argument("--pitch-std", type=float, default=0.0, help="Std dev for pitch perturbation (um)")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed")
    parser.add_argument("--no-superconducting", action="store_true", help="Skip superconducting extraction")
    parser.add_argument("-o", "--output", default=None, help="Output JSON path (sweep report)")
    args = parser.parse_args()

    if not os.path.isfile(args.manifest):
        print(f"Manifest not found: {args.manifest}", file=sys.stderr)
        return 1

    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    result = run_sweep(
        args.manifest,
        args.routing,
        n_samples=args.samples,
        dimension_std_um=args.dimension_std,
        pitch_std_um=args.pitch_std,
        seed=args.seed,
        run_superconducting=not args.no_superconducting,
        script_dir=script_dir,
        repo_root=repo_root,
    )
    out_path = args.output
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"Wrote {out_path}")
    else:
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
