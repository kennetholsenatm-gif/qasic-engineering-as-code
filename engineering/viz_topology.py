"""
Visualize logical topology (and optional logical-to-physical mapping from routing).
Draws the interaction graph; if a routing JSON is provided, annotates nodes with
the QAOA mapping (logical -> physical).

Usage:
  python engineering/viz_topology.py --topology linear_chain --qubits 3
  python engineering/viz_topology.py --topology star --qubits 4 -o star.png
  python engineering/viz_topology.py routing_result.json -o routing_viz.png
  python engineering/viz_topology.py --topology star --qubits 4 routing_result.json -o out.png
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Repo root for asic.topology_builder
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    _HAS_MPL = True
except ImportError:
    _HAS_MPL = False


def load_routing_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def draw_topology(
    edges: list[tuple[int, int]],
    n_qubits: int,
    mapping: list[tuple[int, int]] | None = None,
    title: str = "Logical topology",
    out_path: str | None = None,
) -> None:
    """
    Draw the logical topology graph. If mapping is provided (list of (logical, physical)),
    annotate each node with "Lx → Py".
    """
    if not _HAS_MPL:
        raise RuntimeError("matplotlib is required. Install with: pip install matplotlib")

    # Layout: place nodes in a circle for clarity
    theta = np.linspace(0, 2 * np.pi, n_qubits, endpoint=False)
    pos = {i: (np.cos(t), np.sin(t)) for i, t in enumerate(theta)}

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.set_aspect("equal")

    # Edges
    for a, b in edges:
        x = [pos[a][0], pos[b][0]]
        y = [pos[a][1], pos[b][1]]
        ax.plot(x, y, "k-", lw=1.5, zorder=0)

    # Nodes
    phys_by_log = {}
    if mapping:
        for log, phys in mapping:
            phys_by_log[log] = phys

    for i in range(n_qubits):
        x, y = pos[i]
        ax.scatter(x, y, s=400, c="steelblue", edgecolors="black", linewidths=1.5, zorder=1)
        if mapping and i in phys_by_log:
            label = f"L{i}\n→ P{phys_by_log[i]}"
        else:
            label = str(i)
        ax.annotate(
            label,
            (x, y),
            ha="center",
            va="center",
            fontsize=10,
            fontweight="bold",
            zorder=2,
        )

    ax.axis("off")
    ax.set_title(title)
    plt.tight_layout()
    if out_path:
        plt.savefig(out_path, dpi=120, bbox_inches="tight")
        print(f"Saved to {out_path}")
    else:
        plt.show()
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Visualize logical topology and optional routing mapping.",
    )
    parser.add_argument(
        "routing_json",
        nargs="?",
        default=None,
        help="Optional routing JSON from routing_qubo_qaoa.py -o (for mapping and/or topology).",
    )
    parser.add_argument(
        "--topology",
        "-t",
        type=str,
        default="linear_chain",
        choices=["linear", "linear_chain", "star", "repeater", "repeater_chain"],
        help="Named topology (default: linear_chain).",
    )
    parser.add_argument(
        "--qubits",
        "-n",
        type=int,
        default=None,
        metavar="N",
        help="Number of logical qubits (default: from routing JSON or 3).",
    )
    parser.add_argument(
        "--hub",
        type=int,
        default=0,
        help="Hub node index for star topology (default: 0).",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        metavar="FILE",
        help="Output image path (e.g. topology.png).",
    )
    args = parser.parse_args()

    if not _HAS_MPL:
        print("matplotlib is required: pip install matplotlib", file=sys.stderr)
        return 1

    n_qubits = args.qubits
    mapping = None
    title = f"Logical topology: {args.topology}"

    if args.routing_json:
        path = Path(args.routing_json)
        if not path.is_file():
            print(f"File not found: {path}", file=sys.stderr)
            return 1
        try:
            data = load_routing_json(str(path))
        except (OSError, json.JSONDecodeError) as e:
            print(f"Error loading {path}: {e}", file=sys.stderr)
            return 1
        if n_qubits is None:
            n_qubits = data.get("num_logical_qubits", 3)
        raw = data.get("mapping", [])
        if raw:
            mapping = [
                (m["logical"], m["physical"])
                for m in raw
                if isinstance(m, dict) and "logical" in m and "physical" in m
            ]
            if mapping:
                title = f"{args.topology} + QAOA mapping"

    if n_qubits is None:
        n_qubits = 3

    try:
        from asic.topology_builder import get_topology
        topo, _ = get_topology(args.topology, n_qubits, hub=args.hub)
        edges = list(topo.edges)
    except Exception as e:
        print(f"Topology error: {e}", file=sys.stderr)
        return 1

    try:
        draw_topology(
            edges=edges,
            n_qubits=n_qubits,
            mapping=mapping,
            title=title,
            out_path=args.output,
        )
    except Exception as e:
        print(f"Visualization error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
