"""
Demo: rf-SQUID / flux-tunable superconducting meta-atom spectrum and sweet spots.
Uses scqubits to diagonalize the Hamiltonian and sweep external flux; optionally
identifies sweet spots (min d(transition frequency)/d(flux)).
Ref: Engineering as Code Distributed Computational Roadmap; Computational Materials
     Science and Simulation Architectures for Cryogenic Quantum Metamaterials.

Requires: pip install scqubits (optional; run without it to print install message).
CLI: --flux-points N, --evals M, --plot (save spectrum plot), --sweet-spots (report).
"""
from __future__ import annotations

import argparse
import sys
from typing import Any

try:
    import numpy as np
    import scqubits as scq
except ImportError as e:
    scq = None
    np = None
    _IMPORT_ERROR = e


def _fluxonium_spectrum_and_sweet_spots(
    flux_vals: np.ndarray,
    evals_count: int,
    EJ: float = 8.9,
    EC: float = 2.5,
    EL: float = 0.5,
) -> tuple[np.ndarray, np.ndarray, list[float]]:
    """
    Sweep external flux for a Fluxonium (rf-SQUID-like) circuit; return eigenvalues
    and flux values where d(omega_01)/d(flux) is minimal (sweet spots).
    """
    evals_list: list[np.ndarray] = []
    for phi_ext in flux_vals:
        qubit = scq.Fluxonium(EJ=EJ, EC=EC, EL=EL, flux=float(phi_ext))
        evals, _ = qubit.eigensys(evals_count=evals_count)
        evals_list.append(evals)
    evals_grid = np.array(evals_list)
    # Transition frequency 0->1 (scqubits returns energies in GHz)
    if evals_grid.shape[1] >= 2:
        omega_01 = evals_grid[:, 1] - evals_grid[:, 0]
        d_omega = np.gradient(omega_01, flux_vals)
        abs_d_omega = np.abs(d_omega)
        # Sweet spots: local minima of |d(omega)/d(flux)|
        sweet_flux: list[float] = []
        for i in range(1, len(flux_vals) - 1):
            if abs_d_omega[i] <= abs_d_omega[i - 1] and abs_d_omega[i] <= abs_d_omega[i + 1]:
                sweet_flux.append(float(flux_vals[i]))
    else:
        sweet_flux = []
    return flux_vals, evals_grid, sweet_flux


def run_demo(
    flux_points: int = 51,
    evals_count: int = 6,
    plot: bool = False,
    sweet_spots: bool = True,
    out_path: str | None = None,
) -> dict[str, Any]:
    flux_vals = np.linspace(-0.5, 0.5, flux_points)
    flux_vals, evals_grid, sweet_flux = _fluxonium_spectrum_and_sweet_spots(
        flux_vals, evals_count=evals_count
    )
    result: dict[str, Any] = {
        "flux_min": float(flux_vals.min()),
        "flux_max": float(flux_vals.max()),
        "evals_shape": list(evals_grid.shape),
        "sweet_spots_flux": sweet_flux,
    }
    if sweet_spots and sweet_flux:
        print("Sweet spots (flux values with minimal d(omega_01)/d(flux)):")
        for f in sweet_flux:
            print(f"  phi_ext/phi0 = {f:.4f}")
    if plot or out_path:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            print("matplotlib not installed; skip plot.", file=sys.stderr)
        else:
            fig, ax = plt.subplots()
            for i in range(evals_grid.shape[1]):
                ax.plot(flux_vals, evals_grid[:, i], label=f"E_{i}")
            ax.set_xlabel(r"$\Phi_{\mathrm{ext}}/\Phi_0$")
            ax.set_ylabel("Energy (GHz)")
            ax.set_title("Fluxonium spectrum (scqubits)")
            ax.legend(loc="best", fontsize=8)
            fig.tight_layout()
            path = out_path or "squid_spectrum_scqubits.png"
            fig.savefig(path, dpi=120)
            plt.close(fig)
            print(f"Plot saved to {path}")
            result["plot_path"] = path
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="rf-SQUID/Fluxonium spectrum and sweet spots via scqubits"
    )
    parser.add_argument(
        "--flux-points",
        type=int,
        default=51,
        help="Number of flux points in sweep (default: 51).",
    )
    parser.add_argument(
        "--evals",
        type=int,
        default=6,
        help="Number of eigenvalues to compute per point (default: 6).",
    )
    parser.add_argument(
        "--plot",
        action="store_true",
        help="Save spectrum plot to PNG.",
    )
    parser.add_argument(
        "--sweet-spots",
        action="store_true",
        default=True,
        help="Report sweet spots (default: True).",
    )
    parser.add_argument(
        "--no-sweet-spots",
        action="store_false",
        dest="sweet_spots",
        help="Do not report sweet spots.",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output path for plot (default: squid_spectrum_scqubits.png).",
    )
    args = parser.parse_args()

    if scq is None or np is None:
        print(
            "scqubits is not installed. Install with: pip install scqubits",
            file=sys.stderr,
        )
        print("This demo is optional; the rest of the repo runs without it.", file=sys.stderr)
        return 0

    run_demo(
        flux_points=args.flux_points,
        evals_count=args.evals,
        plot=args.plot,
        sweet_spots=args.sweet_spots,
        out_path=args.output,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
