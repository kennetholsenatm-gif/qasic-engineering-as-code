"""
Inverse design for programmable metasurface: map desired quantum topology / beam steering
to phase shifts (0--2*pi) per meta-atom. Trained to match target phase profiles or
downstream EM/quantum metrics.
Ref: Holographic Metasurfaces and Cryogenic Architectures for Scalable Quantum Computing
     and Satellite Communications.

CLI: run on CPU/CUDA (--device), optionally use routing result (--routing-result),
write result to JSON (-o/--output). With -o, also writes phase array to .npy alongside.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from datetime import datetime
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim


class MetasurfaceInverseNet(nn.Module):
    """
    MLP: target topology/beam features -> phase profile over meta-atoms.
    Output phases in [0, 2*pi] for each of num_meta_atoms elements.
    """

    def __init__(
        self,
        target_params_size: int,
        num_meta_atoms: int,
        hidden: tuple[int, ...] = (128, 256, 512, 1024),
    ):
        super().__init__()
        self.target_params_size = target_params_size
        self.num_meta_atoms = num_meta_atoms
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
        return: (batch, num_meta_atoms) phases in [0, 2*pi].
        """
        raw = self.net(x)
        return self.sigmoid(raw) * (2 * math.pi)


def create_model(
    target_topology_features: int = 10,
    num_meta_atoms: int = 1000,
    device: str | torch.device = "cpu",
) -> MetasurfaceInverseNet:
    """Build model and move to device."""
    model = MetasurfaceInverseNet(
        target_params_size=target_topology_features,
        num_meta_atoms=num_meta_atoms,
    )
    return model.to(device)


def example_forward_pass(
    target_topology_features: int = 10,
    num_meta_atoms: int = 1000,
    batch_size: int = 1,
    device: str | torch.device = "cpu",
    seed: Optional[int] = None,
) -> torch.Tensor:
    """
    Run a single forward pass: random target -> phase profile.
    In production, target would come from protocol layer (e.g. desired coupling graph).
    """
    if seed is not None:
        torch.manual_seed(seed)
    model = create_model(target_topology_features, num_meta_atoms, device)
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
    with open(routing_path) as f:
        data = json.load(f)
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
        "--seed",
        type=int,
        default=None,
        help="Random seed for topology vector (when not using --routing-result).",
    )
    args = parser.parse_args()

    target_topology_features = args.target_dim
    num_meta_atoms = args.meta_atoms
    device = _resolve_device(args.device)

    if args.seed is not None:
        torch.manual_seed(args.seed)

    model = create_model(target_topology_features, num_meta_atoms, device)
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

    print("Metasurface Inverse Design Network")
    print(f"  Device: {device}")
    print(f"  Input: target topology features dim = {target_topology_features}")
    print(f"  Output: phase shifts for {predicted_phase_array.shape[1]} meta-atoms")
    print(f"  Phase range: [{phase_min:.3f}, {phase_max:.3f}] (expect [0, 2*pi])")

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
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        with open(out_path, "w") as f:
            json.dump(out, f, indent=2)
        print(f"  Result written to {out_path}, phases to {npy_path}")


if __name__ == "__main__":
    main()
