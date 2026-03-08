# Topology Builder and Visualizer

The **topology builder** provides named physical topologies (linear chain, star, repeater chain) and an **interaction matrix** used by the QUBO routing problem: which logical-qubit pairs must interact and at what “distance” cost. The **visualizer** draws the topology graph (matplotlib) and can overlay the logical→physical mapping from a routing result.

## Named topologies

| Name | Description | Parameters |
|------|-------------|------------|
| `linear_chain` / `linear` | Edges (i, i+1); default ASIC-style chain. | `n_qubits` |
| `star` | One hub connected to all others. | `n_qubits`, `hub` (default 0) |
| `repeater_chain` / `repeater` | Same as linear chain (repeater nodes in a line). | `n_qubits` |

API (from repo root so `asic` is importable):

```python
from asic.topology_builder import get_topology

topology, interaction_matrix = get_topology("linear_chain", 4)
topology, interaction_matrix = get_topology("star", 4, hub=0)
```

- **`topology`**: `Topology(n_qubits, edges)` from `asic.topology`.
- **`interaction_matrix`**: Symmetric 0/1 matrix; entry (i,j)=1 means logical qubits i and j interact in the QUBO objective. Used by `build_routing_qubo(..., interaction_matrix=...)` in `routing_qubo_qaoa.py`.

## Routing with a topology

From repo root:

```bash
python engineering/routing_qubo_qaoa.py --topology linear_chain --qubits 4 -o out.json
python engineering/routing_qubo_qaoa.py --topology star --qubits 4 --hub 0 -o star_routing.json
```

Choices for `--topology`: `linear`, `linear_chain`, `star`, `repeater`, `repeater_chain`. The routing JSON includes `"topology": "<name>"` and `mapping` (logical → physical).

## Visualizer

Requires **matplotlib** (`pip install -r engineering/requirements-engineering.txt` or `pip install matplotlib`).

**Topology only (no routing result):**

```bash
python engineering/viz_topology.py --topology star --qubits 4 -o star.png
```

**Topology + mapping from routing JSON:**

```bash
python engineering/viz_topology.py star_routing.json -o star.png
```

Options: `--topology`, `--qubits`/`-n`, `--hub` (for star), `-o` output path. If a routing JSON path is given, the graph labels nodes with the logical→physical mapping (e.g. `L0 → P2`).

## See also

- **QUANTUM_ASIC.md** — protocol-layer topology and gate set.
- **engineering/README.md** — routing CLI and pipeline.
