"""
Reinforcement-learning-style routing fallback: improve logical->physical mapping by
local search (e.g. swap-based) to minimize the same cost as the QUBO (distance + optional decoherence).
Reads/writes the same JSON format as routing_qubo_qaoa.py so it can be used with --routing-method rl.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


def routing_cost(
    mapping: list[tuple[int, int]],
    num_physical: int,
    interaction_matrix: np.ndarray,
    distance_penalty_scale: float = 1.0,
    node_decoherence_rates: np.ndarray | None = None,
    decoherence_penalty_scale: float = 1.0,
) -> float:
    """Compute QUBO-like cost: sum of distance penalties for interacting pairs + decoherence linear terms."""
    logical_to_phys = {m[0]: m[1] for m in mapping}
    cost = 0.0
    for i in range(len(mapping)):
        for j in range(len(mapping)):
            if i != j and interaction_matrix[i, j] != 0:
                ji, jj = logical_to_phys[i], logical_to_phys[j]
                cost += distance_penalty_scale * abs(ji - jj)
    if node_decoherence_rates is not None and len(node_decoherence_rates) >= num_physical:
        for _, j in mapping:
            cost += decoherence_penalty_scale * float(node_decoherence_rates[j])
    return cost


def random_mapping(num_logical: int, num_physical: int, rng: np.random.Generator) -> list[tuple[int, int]]:
    perm = rng.permutation(num_physical)
    return [(i, int(perm[i])) for i in range(num_logical)]


def swap_mapping(mapping: list[tuple[int, int]], a: int, b: int) -> list[tuple[int, int]]:
    """Swap physical assignments of logical a and logical b."""
    out = list(mapping)
    out[a] = (mapping[a][0], mapping[b][1])
    out[b] = (mapping[b][0], mapping[a][1])
    return out


def improve_routing(
    num_logical: int,
    num_physical: int,
    interaction_matrix: np.ndarray,
    distance_penalty_scale: float = 1.0,
    node_decoherence_rates: np.ndarray | None = None,
    decoherence_penalty_scale: float = 1.0,
    steps: int = 500,
    seed: int | None = None,
) -> tuple[list[tuple[int, int]], float]:
    """Hill-climbing: start from random mapping, try random swaps, keep if cost improves."""
    rng = np.random.default_rng(seed)
    mapping = random_mapping(num_logical, num_physical, rng)
    cost = routing_cost(
        mapping, num_physical, interaction_matrix,
        distance_penalty_scale, node_decoherence_rates, decoherence_penalty_scale,
    )
    for _ in range(steps):
        i, j = rng.integers(0, num_logical, size=2)
        if i == j:
            continue
        candidate = swap_mapping(mapping, i, j)
        c2 = routing_cost(
            candidate, num_physical, interaction_matrix,
            distance_penalty_scale, node_decoherence_rates, decoherence_penalty_scale,
        )
        if c2 < cost:
            mapping = candidate
            cost = c2
    return mapping, cost


def main() -> int:
    parser = argparse.ArgumentParser(description="RL-style routing (swap-based local search)")
    parser.add_argument("-o", "--output", type=str, default=None, help="Write routing JSON here")
    parser.add_argument("--qubits", "-n", type=int, default=3, help="Number of logical qubits")
    parser.add_argument("--steps", type=int, default=500, help="Local search steps")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--decoherence-file", type=str, default=None, help="JSON with per-node rates")
    args = parser.parse_args()

    num_logical = args.qubits
    num_physical = num_logical
    interaction_matrix = np.zeros((num_logical, num_logical))
    for i in range(num_logical - 1):
        interaction_matrix[i, i + 1] = 1
        interaction_matrix[i + 1, i] = 1

    node_decoherence_rates = None
    if args.decoherence_file:
        try:
            from engineering.decoherence_rates import get_node_decoherence_rates_from_file
            node_decoherence_rates = get_node_decoherence_rates_from_file(args.decoherence_file)
        except Exception:
            try:
                from decoherence_rates import get_node_decoherence_rates_from_file
                node_decoherence_rates = get_node_decoherence_rates_from_file(args.decoherence_file)
            except Exception:
                pass

    mapping, cost = improve_routing(
        num_logical, num_physical, interaction_matrix,
        node_decoherence_rates=node_decoherence_rates,
        steps=args.steps,
        seed=args.seed,
    )
    print(f"RL routing: cost = {cost:.2f}, mapping = {mapping}")

    if args.output:
        out = {
            "num_logical_qubits": num_logical,
            "num_physical_nodes": num_physical,
            "topology": "linear_chain",
            "solver": "routing_rl",
            "objective_value": float(cost),
            "backend": None,
            "mapping": [{"logical": a, "physical": b} for a, b in mapping],
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
        print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
