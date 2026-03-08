"""
Demo: Open quantum system and TLS-like decoherence via Lindblad master equation.
Uses QuTiP to evolve a qubit under relaxation and dephasing; reports T1/T2-like decay.
Ref: Engineering as Code Distributed Computational Roadmap; Computational Materials
     Science (QuTiP, TLS decoherence, Lindblad).

Requires: pip install qutip (optional; run without it to print install message).
CLI: --gamma1, --gamma2 (decay rates), --tmax, --points (time grid), --plot (save PNG).
"""
from __future__ import annotations

import argparse
import sys
from typing import Any

try:
    import numpy as np
    import qutip as qt
except ImportError:
    qt = None
    np = None


def run_lindblad_demo(
    gamma1: float = 0.1,
    gamma2: float = 0.05,
    tmax: float = 10.0,
    n_points: int = 101,
    plot: bool = False,
    out_path: str | None = None,
) -> dict[str, Any]:
    """
    Single qubit: H = 0 (or small omega for visualization). Collapse operators:
    sqrt(gamma1) * sigmam (relaxation), sqrt(gamma_phi) * sigmaz (dephasing)
    with gamma_phi = gamma2 - gamma1/2 for T2 <= 2*T1. Initial state: |1>.
    Returns expectation of sigmaz (population difference) and optional T1/T2 estimates.
    """
    # Qubit: sigma_z basis; |0> ground, |1> excited
    H = qt.Qobj([[0, 0], [0, 0]])
    rho0 = qt.ket2dm(qt.basis(2, 1))
    tlist = np.linspace(0, tmax, n_points)
    # Relaxation: L = sqrt(gamma1) * sigmam
    sm = qt.sigmam()
    sz = qt.sigmaz()
    c_ops = [np.sqrt(gamma1) * sm]
    # Dephasing: gamma_phi such that 1/T2 = 1/(2*T1) + 1/T_phi
    gamma_phi = max(0, gamma2 - gamma1 / 2.0)
    if gamma_phi > 0:
        c_ops.append(np.sqrt(gamma_phi) * sz)
    e_ops = [sz]
    result = qt.mesolve(H, rho0, tlist, c_ops, e_ops)
    expect_z = np.array(result.expect[0]).flatten()
    result_dict: dict[str, Any] = {
        "tlist": tlist.tolist(),
        "expect_sigmaz": expect_z.tolist(),
        "gamma1": gamma1,
        "gamma2": gamma2,
    }
    if plot or out_path:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            print("matplotlib not installed; skip plot.", file=sys.stderr)
        else:
            fig, ax = plt.subplots()
            ax.plot(tlist, expect_z, label=r"$\langle \sigma_z \rangle$")
            ax.set_xlabel("Time")
            ax.set_ylabel(r"$\langle \sigma_z \rangle$")
            ax.set_title("Qubit decay (Lindblad, QuTiP)")
            ax.legend()
            ax.grid(True, alpha=0.3)
            fig.tight_layout()
            path = out_path or "open_system_qutip.png"
            fig.savefig(path, dpi=120)
            plt.close(fig)
            print(f"Plot saved to {path}")
            result_dict["plot_path"] = path
    return result_dict


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Open quantum system / TLS decoherence demo (QuTiP Lindblad)"
    )
    parser.add_argument(
        "--gamma1",
        type=float,
        default=0.1,
        help="Relaxation rate (T1 = 1/gamma1) (default: 0.1).",
    )
    parser.add_argument(
        "--gamma2",
        type=float,
        default=0.05,
        help="Dephasing rate contribution (default: 0.05).",
    )
    parser.add_argument(
        "--tmax",
        type=float,
        default=10.0,
        help="Evolution time (default: 10).",
    )
    parser.add_argument(
        "--points",
        type=int,
        default=101,
        help="Number of time points (default: 101).",
    )
    parser.add_argument(
        "--plot",
        action="store_true",
        help="Save expectation plot to PNG.",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output path for plot (default: open_system_qutip.png).",
    )
    args = parser.parse_args()

    if qt is None or np is None:
        print(
            "qutip is not installed. Install with: pip install qutip",
            file=sys.stderr,
        )
        print("This demo is optional; the rest of the repo runs without it.", file=sys.stderr)
        return 0

    run_lindblad_demo(
        gamma1=args.gamma1,
        gamma2=args.gamma2,
        tmax=args.tmax,
        n_points=args.points,
        plot=args.plot,
        out_path=args.output,
    )
    print("Lindblad evolution completed (sigmaz expectation over time).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
