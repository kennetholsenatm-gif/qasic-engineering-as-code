"""
Demo: Minimal SuperScreen run (2D London equation, Meissner screening).
If SuperScreen is installed, builds a simple ring device and runs the solver;
otherwise prints an install message and exits.
Ref: Engineering as Code Distributed Computational Roadmap; Computational Materials
     Science (SuperScreen, self/mutual inductance matrices).

Requires: pip install superscreen (optional).
CLI: no arguments. Optional -o PATH to save a simple plot.
"""
from __future__ import annotations

import argparse
import sys

try:
    import superscreen as sc
    from superscreen.geometry import circle
except ImportError:
    sc = None
    circle = None


def run_minimal_demo(save_plot: str | None = None) -> bool:
    """Build a simple superconducting ring, mesh, run solver; return True on success."""
    if sc is None or circle is None:
        return False
    try:
        length_units = "um"
        layer = sc.Layer("base", london_lambda=0.1, thickness=0.025, z0=0)
        film = sc.Polygon.from_difference(
            [circle(3), circle(1)], name="ring", layer="base"
        )
        device = sc.Device(
            "ring",
            layers=[layer],
            films=[film],
            length_units=length_units,
        )
        device.make_mesh(max_edge_length=0.2, smooth=50)
        solution = sc.solve(device, applied_field=sc.ConstantField(1.0))
        if save_plot and solution:
            try:
                solution[0].plot_current_density(save_path=save_plot)
                print(f"Plot saved to {save_plot}")
            except Exception as e:
                print(f"Could not save plot: {e}", file=sys.stderr)
    except Exception as e:
        print(f"SuperScreen demo error: {e}", file=sys.stderr)
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Minimal SuperScreen demo (2D London equation)"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Save current-density plot to this path.",
    )
    args = parser.parse_args()

    if sc is None or circle is None:
        print(
            "SuperScreen is not installed. Install with: pip install superscreen",
            file=sys.stderr,
        )
        print("This demo is optional; the rest of the repo runs without it.", file=sys.stderr)
        return 0

    if run_minimal_demo(save_plot=args.output):
        print("SuperScreen demo completed (ring device, applied field).")
    else:
        print("SuperScreen demo failed.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
