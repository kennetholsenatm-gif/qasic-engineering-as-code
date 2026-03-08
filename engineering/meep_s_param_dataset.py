"""
Generate (config, S-parameters) dataset for training the forward prediction network.
When Meep (pymeep) is available, run a minimal FDTD simulation per config and extract
S-parameter-like outputs. When not available, use a deterministic formula from config
so the dataset format and training path are the same.
Ref: Forward CNN for S-parameters; FEM/FDTD data pipeline.
"""
from __future__ import annotations

import argparse
import json
import os
from typing import Optional

import numpy as np

try:
    import meep as mp
    _HAS_MEEP = True
except ImportError:
    mp = None
    _HAS_MEEP = False


def _simulate_one_meep(config: np.ndarray, output_size: int) -> np.ndarray:
    """
    Run one Meep FDTD simulation for a simple geometry parameterized by config;
    return S-parameter-like vector of length output_size.
    When Meep is installed, extend this to run actual FDTD and mode decomposition
    for S11, S21, etc. See MEEP docs and examples for S-parameter calculations.
    """
    if not _HAS_MEEP:
        raise RuntimeError("Meep not installed (pip install pymeep or use conda)")
    # Stub: run minimal simulation when possible; replace with real S-param extraction
    try:
        res = 16
        cell = mp.Vector3(8, 8, 0)
        sim = mp.Simulation(
            cell_size=cell,
            resolution=res,
            default_material=mp.Medium(epsilon=1),
        )
        sim.run(until=5)
    except Exception:
        pass
    # Output: config-dependent placeholder; replace with sim S-param results
    out = np.zeros(output_size, dtype=np.float64)
    for i in range(min(output_size, config.size)):
        out[i] = float(np.tanh(config[i]) * 0.2 + 0.5)
    for i in range(config.size, output_size):
        out[i] = 0.3 + 0.1 * (i % 3)
    return out


def _simulate_one_formula(config: np.ndarray, output_size: int, seed: Optional[int] = None) -> np.ndarray:
    """Deterministic formula-based S-like output when Meep is not used (config -> S)."""
    if seed is not None:
        rng = np.random.default_rng(seed)
    else:
        rng = np.random.default_rng(42)
    # Simple polynomial + sin so the forward net can learn something
    out = np.zeros(output_size)
    for j in range(output_size):
        s = 0.0
        for i, c in enumerate(config.ravel()):
            s += c * (0.1 * (i + 1) + 0.05 * (j + 1)) + 0.02 * np.sin(c * 3)
        out[j] = 0.5 + 0.3 * np.tanh(s) + 0.01 * (rng.random() - 0.5)
    return out.astype(np.float64)


def generate_dataset(
    num_samples: int,
    config_size: int,
    output_size: int,
    out_path: str,
    use_meep: bool = False,
    seed: Optional[int] = None,
) -> None:
    """
    Generate num_samples (config, S) pairs and save to out_path (.npz or .json + .npy).
    use_meep: if True and Meep available, run FDTD per sample; else use formula.
    """
    rng = np.random.default_rng(seed)
    configs = rng.standard_normal((num_samples, config_size)).astype(np.float32)
    targets = np.zeros((num_samples, output_size), dtype=np.float32)
    for i in range(num_samples):
        if use_meep and _HAS_MEEP:
            try:
                targets[i] = _simulate_one_meep(configs[i], output_size)
            except Exception:
                targets[i] = _simulate_one_formula(configs[i], output_size, seed=seed + i if seed else None)
        else:
            targets[i] = _simulate_one_formula(configs[i], output_size, seed=seed + i if seed else None)
    base, ext = os.path.splitext(out_path)
    if ext.lower() == ".npz":
        np.savez(out_path, config=configs, S_params=targets, config_size=config_size, output_size=output_size)
    else:
        np.save(base + "_config.npy", configs)
        np.save(base + "_S.npy", targets)
        meta = {"config_size": config_size, "output_size": output_size, "num_samples": num_samples}
        with open(base + "_meta.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
    print(f"Wrote {num_samples} samples to {out_path} (config_size={config_size}, output_size={output_size})")
    # Optional: log to MLflow when MLFLOW_TRACKING_URI is set
    try:
        from storage.artifacts_mlflow import log_artifact_run, is_enabled
        if is_enabled():
            artifacts = [out_path] if os.path.isfile(out_path) else [base + "_config.npy", base + "_S.npy", base + "_meta.json"]
            artifacts = [p for p in artifacts if os.path.isfile(p)]
            if artifacts:
                log_artifact_run(
                    "meep_s_param_dataset",
                    params={"num_samples": num_samples, "config_size": config_size, "output_size": output_size, "use_meep": use_meep},
                    tags={"source": "meep_s_param_dataset"},
                    artifacts=artifacts,
                )
    except Exception:
        pass


def load_dataset(path: str) -> tuple[np.ndarray, np.ndarray]:
    """Load (config, S) from .npz or from base_config.npy + base_S.npy + base_meta.json."""
    base, ext = os.path.splitext(path)
    if ext.lower() == ".npz" and os.path.isfile(path):
        data = np.load(path)
        return data["config"], data["S_params"]
    if os.path.isfile(base + "_config.npy") and os.path.isfile(base + "_S.npy"):
        return np.load(base + "_config.npy"), np.load(base + "_S.npy")
    raise FileNotFoundError(f"Dataset not found: {path} or {base}_config.npy / {base}_S.npy")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate (config, S-params) dataset for forward net")
    parser.add_argument("-o", "--output", default="fdtd_dataset.npz", help="Output .npz or base name")
    parser.add_argument("--samples", type=int, default=100, help="Number of samples")
    parser.add_argument("--config-size", type=int, default=20)
    parser.add_argument("--output-size", type=int, default=4)
    parser.add_argument("--meep", action="store_true", help="Use Meep FDTD when available")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    generate_dataset(
        num_samples=args.samples,
        config_size=args.config_size,
        output_size=args.output_size,
        out_path=args.output,
        use_meep=args.meep,
        seed=args.seed,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
