"""
Inverse design for programmable metasurface: map desired quantum topology / beam steering
to phase shifts per meta-atom. Trained to match target phase profiles or downstream
EM/quantum metrics.
Ref: Holographic Metasurfaces and Cryogenic Architectures for Scalable Quantum Computing
     and Satellite Communications; Engineering as Code Distributed Computational Roadmap.

Output range: default [0, 2*pi]. Optional --phase-band pi (or e.g. 3.033,3.284) constrains
phases to a narrow band around pi to match Cryo-CMOS thermal budget (18 nW/cell, 10 mK).

CLI: run on CPU/CUDA (--device), optionally use routing result (--routing-result),
--phase-band for Cryo-CMOS constraint, write result to JSON (-o/--output). With -o,
also writes phase array to .npy alongside.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim


def parse_phase_band(s: str | None) -> tuple[float, float] | None:
    """
    Parse --phase-band: "pi" -> (pi - 0.14, pi + 0.14); "lo,hi" -> (lo, hi) in radians.
    Returns None for full [0, 2*pi].
    """
    if not s or s.lower() == "full":
        return None
    if s.strip().lower() == "pi":
        return (math.pi - 0.14, math.pi + 0.14)
    parts = [p.strip() for p in s.split(",")]
    if len(parts) != 2:
        raise ValueError(f"phase_band must be 'pi' or 'lo,hi', got {s!r}")
    return (float(parts[0]), float(parts[1]))


class MetasurfaceInverseNet(nn.Module):
    """
    MLP: target topology/beam features -> phase profile over meta-atoms.
    Output phases in [0, 2*pi] by default, or in [phase_lo, phase_hi] when phase band
    is set (Cryo-CMOS constraint: narrow band around pi).
    """

    def __init__(
        self,
        target_params_size: int,
        num_meta_atoms: int,
        hidden: tuple[int, ...] = (128, 256, 512, 1024),
        phase_lo: float | None = None,
        phase_hi: float | None = None,
    ):
        super().__init__()
        self.target_params_size = target_params_size
        self.num_meta_atoms = num_meta_atoms
        self.phase_lo = phase_lo
        self.phase_hi = phase_hi
        layers = []
        prev = target_params_size
        for h in hidden:
            layers.append(nn.Linear(prev, h))
            layers.append(nn.ReLU(inplace=True))
            prev = h
        layers.append(nn.Linear(prev, num_meta_atoms))
        self.net = nn.Sequential(*layers)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        x: (batch, target_params_size) - e.g. desired Bell-pair locations, steering angles.
        return: (batch, num_meta_atoms) phases in [0, 2*pi] or [phase_lo, phase_hi].
        """
        raw = self.net(x)
        if self.phase_lo is not None and self.phase_hi is not None:
            return self.sigmoid(raw) * (self.phase_hi - self.phase_lo) + self.phase_lo
        return self.sigmoid(raw) * (2 * math.pi)


def create_model(
    target_topology_features: int = 10,
    num_meta_atoms: int = 1000,
    device: str | torch.device = "cpu",
    phase_band: tuple[float, float] | None = None,
) -> MetasurfaceInverseNet:
    """Build model and move to device. phase_band=(lo, hi) constrains output to [lo, hi] rad."""
    model = MetasurfaceInverseNet(
        target_params_size=target_topology_features,
        num_meta_atoms=num_meta_atoms,
        phase_lo=phase_band[0] if phase_band else None,
        phase_hi=phase_band[1] if phase_band else None,
    )
    return model.to(device)


def example_forward_pass(
    target_topology_features: int = 10,
    num_meta_atoms: int = 1000,
    batch_size: int = 1,
    device: str | torch.device = "cpu",
    seed: Optional[int] = None,
    phase_band: tuple[float, float] | None = None,
) -> torch.Tensor:
    """
    Run a single forward pass: random target -> phase profile.
    In production, target would come from protocol layer (e.g. desired coupling graph).
    """
    if seed is not None:
        torch.manual_seed(seed)
    model = create_model(
        target_topology_features, num_meta_atoms, device, phase_band=phase_band
    )
    model.eval()
    desired_topology = torch.randn(batch_size, target_topology_features, device=device)
    with torch.no_grad():
        phase_array = model(desired_topology)
    return phase_array


def training_step_stub(
    model: MetasurfaceInverseNet,
    target_batch: torch.Tensor,
    target_phase_batch: torch.Tensor,
    lr: float = 0.001,
) -> float:
    """
    One training step: MSE between predicted phase profile and target phase profile.
    In practice, loss could be downstream (e.g. EM simulation or fidelity).
    """
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)
    model.train()
    optimizer.zero_grad()
    pred = model(target_batch)
    loss = criterion(pred, target_phase_batch)
    loss.backward()
    optimizer.step()
    return float(loss.item())


def _resolve_device(device_str: str) -> torch.device:
    if device_str == "auto":
        if torch.cuda.is_available():
            return torch.device("cuda")
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")
    return torch.device(device_str)


def _topology_from_routing(routing_path: str, target_dim: int, device: torch.device) -> torch.Tensor:
    """Build a topology feature vector from a routing_qubo_qaoa.py JSON result (mapping + backend)."""
    try:
        with open(routing_path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Routing result file not found: {routing_path}") from None
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in routing result {routing_path}: {e}") from e
    except OSError as e:
        raise OSError(f"Cannot read routing result {routing_path}: {e}") from e
    mapping = data.get("mapping", [])
    backend = data.get("backend") or ""
    # Flatten mapping (logical -> physical) and pad/crop to target_dim
    flat = []
    for m in mapping:
        flat.extend([float(m.get("logical", 0)), float(m.get("physical", 0))])
    for c in backend:
        flat.append(float(ord(c) % 256) / 256.0)
    while len(flat) < target_dim:
        flat.append(0.0)
    vec = torch.tensor(flat[:target_dim], dtype=torch.float32, device=device).unsqueeze(0)
    return vec


def main() -> None:
    parser = argparse.ArgumentParser(description="Metasurface inverse design: topology -> phase profile")
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        choices=("cpu", "cuda", "mps", "auto"),
        help="Device to run the model on (default: auto = cuda if available else cpu).",
    )
    parser.add_argument(
        "--routing-result",
        type=str,
        default=None,
        metavar="FILE",
        help="Optional JSON from routing_qubo_qaoa.py -o; use its mapping/backend as topology input.",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        metavar="FILE",
        help="Write result (device, phase stats, optional routing ref) to JSON; phase array to same base + .npy.",
    )
    parser.add_argument(
        "--target-dim",
        type=int,
        default=10,
        help="Target topology feature dimension (default: 10).",
    )
    parser.add_argument(
        "--meta-atoms",
        type=int,
        default=1000,
        help="Number of meta-atoms in phase profile (default: 1000).",
    )
    parser.add_argument(
        "--phase-band",
        type=str,
        default=None,
        metavar="pi|lo,hi",
        help="Constrain phases to narrow band: 'pi' (pi±0.14 rad) or 'lo,hi' in radians (Cryo-CMOS). Default: full [0, 2*pi].",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for topology vector (when not using --routing-result).",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="mlp",
        choices=("mlp", "gnn"),
        help="Model type: mlp (default) or gnn (graph neural network; requires --routing-result).",
    )
    args = parser.parse_args()

    target_topology_features = args.target_dim
    num_meta_atoms = args.meta_atoms
    device = _resolve_device(args.device)
    phase_band = None
    if args.phase_band:
        phase_band = parse_phase_band(args.phase_band)

    if args.seed is not None:
        torch.manual_seed(args.seed)

    use_gnn = args.model.lower() == "gnn"
    if use_gnn:
        if not args.routing_result or not os.path.isfile(args.routing_result):
            raise FileNotFoundError("GNN model requires --routing-result (routing JSON).")
        try:
            from engineering.metasurface_inverse_gnn import (
                routing_json_to_graph,
                create_gnn_model,
            )
        except ImportError:
            from metasurface_inverse_gnn import (
                routing_json_to_graph,
                create_gnn_model,
            )
        node_feature_dim = min(8, target_topology_features)
        model = create_gnn_model(
            node_feature_dim=node_feature_dim,
            num_meta_atoms=num_meta_atoms,
            device=device,
            phase_band=phase_band,
        )
        x, edge_index = routing_json_to_graph(args.routing_result, node_feature_dim)
        x = x.to(device)
        edge_index = edge_index.to(device)
        routing_ref = {"file": args.routing_result}
        model.eval()
        with torch.no_grad():
            predicted_phase_array = model(x, edge_index)
    else:
        model = create_model(
            target_topology_features, num_meta_atoms, device, phase_band=phase_band
        )
        if args.routing_result and os.path.isfile(args.routing_result):
            desired_topology = _topology_from_routing(args.routing_result, target_topology_features, device)
            routing_ref = {"file": args.routing_result}
        else:
            desired_topology = torch.randn(1, target_topology_features, device=device)
            routing_ref = None
        model.eval()
        with torch.no_grad():
            predicted_phase_array = model(desired_topology)

    phase = predicted_phase_array[0].cpu().numpy()
    phase_min = float(phase.min())
    phase_max = float(phase.max())
    phase_mean = float(phase.mean())

    phase_range_note = "[0, 2*pi]" if phase_band is None else f"[{phase_band[0]:.3f}, {phase_band[1]:.3f}]"
    print("Metasurface Inverse Design Network")
    print(f"  Device: {device}")
    print(f"  Input: target topology features dim = {target_topology_features}")
    print(f"  Output: phase shifts for {predicted_phase_array.shape[1]} meta-atoms")
    print(f"  Phase range: [{phase_min:.3f}, {phase_max:.3f}] (expect {phase_range_note})")

    if args.output:
        out_path = args.output
        base, _ = os.path.splitext(out_path)
        npy_path = base + "_phases.npy"
        np.save(npy_path, phase)
        out = {
            "device": str(device),
            "target_topology_features": target_topology_features,
            "num_meta_atoms": num_meta_atoms,
            "phase_min": phase_min,
            "phase_max": phase_max,
            "phase_mean": phase_mean,
            "phase_array_path": os.path.basename(npy_path),
            "routing_result": routing_ref,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        if phase_band is not None:
            out["phase_band_lo"] = phase_band[0]
            out["phase_band_hi"] = phase_band[1]
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(out, f, indent=2)
        except OSError as e:
            raise OSError(f"Cannot write output {out_path}: {e}") from e
        print(f"  Result written to {out_path}, phases to {npy_path}")


if __name__ == "__main__":
    main()
