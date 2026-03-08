"""
Benchmark MLP vs GNN inverse design (Graph-Theoretic Inverse Design whitepaper).
Runs both models on the same topology (from routing JSON or random); reports phase stats,
thermodynamic compliance, and optional MSE to a synthetic target (e.g. π-baseline).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from typing import Any

import numpy as np
import torch

try:
    from engineering.metasurface_inverse_net import (
        create_model,
        _topology_from_routing,
        parse_phase_band,
        _resolve_device,
    )
    from engineering.metasurface_inverse_gnn import (
        routing_json_to_graph,
        create_gnn_model,
    )
    from engineering.thermodynamic_validator import phase_thermodynamic_report
except ImportError:
    from metasurface_inverse_net import (
        create_model,
        _topology_from_routing,
        parse_phase_band,
        _resolve_device,
    )
    from metasurface_inverse_gnn import routing_json_to_graph, create_gnn_model
    from thermodynamic_validator import phase_thermodynamic_report


def run_mlp(
    device: torch.device,
    routing_path: str | None,
    target_dim: int,
    num_meta_atoms: int,
    phase_band: tuple[float, float] | None,
    seed: int | None,
) -> np.ndarray:
    """Run MLP forward; return phase array (1D) in radians."""
    model = create_model(
        target_topology_features=target_dim,
        num_meta_atoms=num_meta_atoms,
        device=device,
        phase_band=phase_band,
    )
    if seed is not None:
        torch.manual_seed(seed)
    if routing_path and os.path.isfile(routing_path):
        x = _topology_from_routing(routing_path, target_dim, device)
    else:
        x = torch.randn(1, target_dim, device=device)
    model.eval()
    with torch.no_grad():
        out = model(x)
    return out[0].cpu().numpy().ravel()


def run_gnn(
    device: torch.device,
    routing_path: str,
    node_feature_dim: int,
    num_meta_atoms: int,
    phase_band: tuple[float, float] | None,
) -> np.ndarray:
    """Run GNN forward; return phase array (1D) in radians. Requires routing JSON."""
    model = create_gnn_model(
        node_feature_dim=node_feature_dim,
        num_meta_atoms=num_meta_atoms,
        device=device,
        phase_band=phase_band,
    )
    x, edge_index = routing_json_to_graph(routing_path, node_feature_dim)
    x, edge_index = x.to(device), edge_index.to(device)
    model.eval()
    with torch.no_grad():
        out = model(x, edge_index)
    return out[0].cpu().numpy().ravel()


def mse_to_target(phases: np.ndarray, target_rad: float) -> float:
    """MSE of phases vs constant target (e.g. math.pi)."""
    return float(np.mean((phases - target_rad) ** 2))


def benchmark(
    routing_path: str | None,
    target_dim: int = 10,
    num_meta_atoms: int = 1000,
    phase_band: tuple[float, float] | None = None,
    device: torch.device | None = None,
    seed: int | None = 42,
    target_rad: float | None = math.pi,
) -> dict[str, Any]:
    """
    Run MLP (and GNN if routing_path given); collect phase stats and thermodynamic report.
    If target_rad is set, include MSE to that target for both.
    """
    if device is None:
        device = _resolve_device("auto")

    result: dict[str, Any] = {
        "routing_path": routing_path,
        "target_dim": target_dim,
        "num_meta_atoms": num_meta_atoms,
        "phase_band": list(phase_band) if phase_band else None,
        "device": str(device),
        "mlp": {},
        "gnn": None,
    }

    # MLP
    try:
        mlp_phases = run_mlp(device, routing_path, target_dim, num_meta_atoms, phase_band, seed)
        result["mlp"]["phase_mean_rad"] = float(np.mean(mlp_phases))
        result["mlp"]["phase_std_rad"] = float(np.std(mlp_phases))
        result["mlp"]["phase_min_rad"] = float(np.min(mlp_phases))
        result["mlp"]["phase_max_rad"] = float(np.max(mlp_phases))
        result["mlp"]["thermodynamic"] = phase_thermodynamic_report(mlp_phases)
        if target_rad is not None:
            result["mlp"]["mse_to_target"] = mse_to_target(mlp_phases, target_rad)
    except Exception as e:
        result["mlp"]["error"] = str(e)

    # GNN (only if we have routing)
    if routing_path and os.path.isfile(routing_path):
        try:
            node_dim = min(8, target_dim)
            gnn_phases = run_gnn(device, routing_path, node_dim, num_meta_atoms, phase_band)
            result["gnn"] = {
                "phase_mean_rad": float(np.mean(gnn_phases)),
                "phase_std_rad": float(np.std(gnn_phases)),
                "phase_min_rad": float(np.min(gnn_phases)),
                "phase_max_rad": float(np.max(gnn_phases)),
                "thermodynamic": phase_thermodynamic_report(gnn_phases),
            }
            if target_rad is not None:
                result["gnn"]["mse_to_target"] = mse_to_target(gnn_phases, target_rad)
        except Exception as e:
            result["gnn"] = {"error": str(e)}

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark MLP vs GNN inverse design: phase stats and thermodynamic compliance.",
    )
    parser.add_argument(
        "--routing-result",
        type=str,
        default=None,
        metavar="FILE",
        help="Routing JSON; used for both MLP topology and GNN (GNN requires this).",
    )
    parser.add_argument(
        "--target-dim",
        type=int,
        default=10,
        help="Target topology feature dimension (default 10).",
    )
    parser.add_argument(
        "--meta-atoms",
        type=int,
        default=1000,
        help="Number of meta-atoms (default 1000).",
    )
    parser.add_argument(
        "--phase-band",
        type=str,
        default=None,
        metavar="pi|lo,hi",
        help="Constrain phases: 'pi' or 'lo,hi' radians (default: full).",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        choices=("auto", "cpu", "cuda", "mps"),
        help="Device (default auto).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for MLP when no routing (default 42).",
    )
    parser.add_argument(
        "--no-target-mse",
        action="store_true",
        help="Do not compute MSE to π target.",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        metavar="FILE",
        help="Write benchmark result JSON here.",
    )
    parser.add_argument(
        "--table",
        action="store_true",
        help="Print a short comparison table to stdout.",
    )
    args = parser.parse_args()

    phase_band = parse_phase_band(args.phase_band) if args.phase_band else None
    device = _resolve_device(args.device)
    target_rad = None if args.no_target_mse else math.pi

    try:
        report = benchmark(
            routing_path=args.routing_result,
            target_dim=args.target_dim,
            num_meta_atoms=args.meta_atoms,
            phase_band=phase_band,
            device=device,
            seed=args.seed,
            target_rad=target_rad,
        )
    except Exception as e:
        print(f"Benchmark failed: {e}", file=sys.stderr)
        return 1

    # Round floats for JSON
    def round_floats(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: round_floats(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [round_floats(x) for x in obj]
        if isinstance(obj, float):
            return round(obj, 6)
        return obj

    report = round_floats(report)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"Wrote {args.output}")

    if args.table:
        print("\n--- MLP vs GNN benchmark ---")
        print(f"  Meta-atoms: {report['num_meta_atoms']}  Phase band: {report['phase_band']}")
        mlp = report.get("mlp", {})
        if "error" in mlp:
            print("  MLP: ERROR", mlp["error"])
        else:
            th = mlp.get("thermodynamic", {})
            print(f"  MLP:  mean={mlp.get('phase_mean_rad')}  in_pi_band={th.get('all_in_pi_band')}  risk={th.get('thermal_risk')}  " + (
                f"mse_pi={mlp.get('mse_to_target')}" if mlp.get("mse_to_target") is not None else ""
            ))
        gnn = report.get("gnn")
        if gnn is None:
            print("  GNN: (no routing JSON, skipped)")
        elif "error" in gnn:
            print("  GNN: ERROR", gnn["error"])
        else:
            th = gnn.get("thermodynamic", {})
            print(f"  GNN:  mean={gnn.get('phase_mean_rad')}  in_pi_band={th.get('all_in_pi_band')}  risk={th.get('thermal_risk')}  " + (
                f"mse_pi={gnn.get('mse_to_target')}" if gnn.get("mse_to_target") is not None else ""
            ))

    return 0


if __name__ == "__main__":
    sys.exit(main())
