"""
Forward prediction network (FEM surrogate): map metasurface configuration (geometry/flux)
to S-parameters or transmission amplitudes. Stub for the whitepaper's CNN that would be
trained on FEM/FDTD-simulated data.
Ref: Engineering as Code Distributed Computational Roadmap; Computational Materials
     Science (forward CNN for S-parameters, near-field).

CLI: --synthetic runs a stub training loop on random (config, target) pairs.
     In production, replace with FEM/FDTD-generated data.
"""
from __future__ import annotations

import argparse
import sys
from typing import Optional

import torch
import torch.nn as nn
import torch.optim as optim


class ForwardPredictionNet(nn.Module):
    """
    Stub: config vector -> scalar or vector (e.g. S11, S21, transmission amplitude).
    In production this would be a CNN trained on FEM-simulated (geometry, flux) -> S-params.
    """

    def __init__(
        self,
        config_size: int = 20,
        output_size: int = 4,
        hidden: tuple[int, ...] = (64, 128, 64),
    ):
        super().__init__()
        self.config_size = config_size
        self.output_size = output_size
        layers = []
        prev = config_size
        for h in hidden:
            layers.append(nn.Linear(prev, h))
            layers.append(nn.ReLU(inplace=True))
            prev = h
        layers.append(nn.Linear(prev, output_size))
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x: (batch, config_size) -> (batch, output_size)."""
        return self.net(x)


def create_model(
    config_size: int = 20,
    output_size: int = 4,
    device: str | torch.device = "cpu",
) -> ForwardPredictionNet:
    model = ForwardPredictionNet(config_size=config_size, output_size=output_size)
    return model.to(device)


def synthetic_training_stub(
    config_size: int = 20,
    output_size: int = 4,
    batch_size: int = 32,
    steps: int = 100,
    lr: float = 0.001,
    device: str | torch.device = "cpu",
    seed: Optional[int] = None,
) -> float:
    """
    Stub training: random (config, target) pairs, MSE loss.
    In production, replace with FEM/FDTD (config -> S-params) data or use --dataset.
    """
    if seed is not None:
        torch.manual_seed(seed)
    model = create_model(config_size, output_size, device)
    optimizer = optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()
    model.train()
    final_loss = 0.0
    for _ in range(steps):
        x = torch.randn(batch_size, config_size, device=device)
        y = torch.randn(batch_size, output_size, device=device)
        optimizer.zero_grad()
        pred = model(x)
        loss = criterion(pred, y)
        loss.backward()
        optimizer.step()
        final_loss = float(loss.item())
    return final_loss


def train_from_dataset(
    dataset_path: str,
    config_size: Optional[int] = None,
    output_size: Optional[int] = None,
    batch_size: int = 32,
    epochs: int = 10,
    lr: float = 0.001,
    device: str | torch.device = "cpu",
    seed: Optional[int] = None,
) -> float:
    """
    Load (config, S_params) from dataset (see meep_s_param_dataset.py), train ForwardPredictionNet with MSE.
    Returns final epoch mean loss.
    """
    try:
        from engineering.meep_s_param_dataset import load_dataset
    except ImportError:
        from meep_s_param_dataset import load_dataset
    configs, S_params = load_dataset(dataset_path)
    if config_size is None:
        config_size = configs.shape[1]
    if output_size is None:
        output_size = S_params.shape[1]
    if seed is not None:
        torch.manual_seed(seed)
    model = create_model(config_size, output_size, device)
    optimizer = optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()
    x = torch.tensor(configs, dtype=torch.float32, device=device)
    y = torch.tensor(S_params, dtype=torch.float32, device=device)
    n = x.size(0)
    model.train()
    final_loss = 0.0
    for epoch in range(epochs):
        perm = torch.randperm(n, device=device)
        epoch_loss = 0.0
        count = 0
        for start in range(0, n, batch_size):
            end = min(start + batch_size, n)
            idx = perm[start:end]
            optimizer.zero_grad()
            pred = model(x[idx])
            loss = criterion(pred, y[idx])
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
            count += 1
        final_loss = epoch_loss / max(count, 1)
    return final_loss


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Forward prediction network stub (config -> S-params placeholder)"
    )
    parser.add_argument(
        "--config-size",
        type=int,
        default=20,
        help="Input config dimension (default: 20).",
    )
    parser.add_argument(
        "--output-size",
        type=int,
        default=4,
        help="Output size (e.g. S11, S21 placeholder) (default: 4).",
    )
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Run stub training on random data.",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=100,
        help="Synthetic training steps (default: 100).",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        choices=("cpu", "cuda", "auto"),
        help="Device (default: cpu).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42).",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=None,
        metavar="PATH",
        help="Train on (config, S-params) dataset from meep_s_param_dataset.py (.npz or base for _config.npy/_S.npy).",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=10,
        help="Epochs when training from --dataset (default: 10).",
    )
    args = parser.parse_args()

    device = args.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    device = torch.device(device)

    if args.dataset:
        loss = train_from_dataset(
            args.dataset,
            config_size=args.config_size,
            output_size=args.output_size,
            epochs=args.epochs,
            device=device,
            seed=args.seed,
        )
        print(f"Training from dataset finished; final MSE loss: {loss:.6f}")
    elif args.synthetic:
        loss = synthetic_training_stub(
            config_size=args.config_size,
            output_size=args.output_size,
            steps=args.steps,
            device=device,
            seed=args.seed,
        )
        print(f"Synthetic training finished; final MSE loss: {loss:.6f}")
        print("In production, train on FEM/FDTD (config -> S-parameters) data.")
    else:
        model = create_model(args.config_size, args.output_size, device)
        x = torch.randn(2, args.config_size, device=device)
        with torch.no_grad():
            y = model(x)
        print(f"Forward pass: input {x.shape} -> output {y.shape}")
        print("Use --synthetic to run stub training on random data.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
