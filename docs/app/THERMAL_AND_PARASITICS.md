# Thermal Stages and Parasitic Extraction

Cryogenic thermal and crosstalk co-simulation: routing topologies and GDS-derived layout drive a **thermal stage report** and **parasitic extraction** so decoherence inputs can be updated from layout.

## Thermal stage report

**Script:** `engineering/thermal_stages.py`

**Inputs:** Routing JSON (physical node / graph) and phase array (`.npy`). Power is proxied from phase deviation from π (aligned with the 18 nW/cell Cryo-CMOS budget in the whitepaper).

**Model:** Lumped thermal network: total power from all cells, then proxy temperatures at 10 mK, 4 K, and 50 K stages using simple resistance scaling. No full FEA; suitable for CI and quick checks.

**Output:** `*_thermal_report.json` with:
- `P_total_nW`, `P_mean_nW_per_cell`
- `T_10mK_K`, `T_4K_K`, `T_50K_K` and limits
- `passed_10mK`, `passed_4K`, `passed_50K`, `passed`

**Pipeline:** Run with `python engineering/run_pipeline.py -o BASE --thermal` (after inverse design). Requires routing and phase outputs.

**Integration:** The thermodynamic validator (`thermodynamic_validator.py`) remains the lightweight π-baseline and thermal-risk check; the thermal stage report is the optional, heavier step that outputs explicit stage temperatures.

## Parasitic extraction

**Script:** `engineering/parasitic_extraction.py`

**Inputs:** Geometry manifest (and optional routing JSON). Cell positions from the manifest; pairwise distances in µm.

**Logic:** Compute Euclidean distances between cells; apply a simple coupling proxy (e.g. scale / distance). Per-node decoherence = base rate + sum of coupling contributions from neighbors.

**Output:** JSON in the same format as `engineering/decoherence_rates.py` expects: `{"nodes": [{"gamma1": ..., "gamma2": ...}, ...]}`. Use this file with `routing_qubo_qaoa.py --decoherence-file` for re-routing with layout-aware decoherence.

**Pipeline:** Run with `python engineering/run_pipeline.py -o BASE --heac --parasitic`. Writes `*_decoherence_from_layout.json`.

## How decoherence files feed back

- **Routing** (`routing_qubo_qaoa.py`, `routing_rl.py`) accepts `--decoherence-file`. Pass the output of parasitic extraction so that physical nodes with higher layout-derived coupling get higher decoherence penalty in the QUBO.
- **Simulation** (`state/channels.py`, `protocols/noise.py`) can use per-node rates from the same file for more realistic noise models.

## Cryo-CMOS / classical interface heat model

If the ASIC uses **deep cryogenic classical logic** (e.g. SFQ or Cryo-CMOS) for control/readout, its dissipation can be included in the thermal budget:

- **CLI:** `thermal_stages.py` accepts `--classical-power-nw N` to add N nW to the total power (lumped). This is a placeholder for per-node or per-control-line power from routing/readout density; future work can feed power from `routing_rl.py` or a control-line activity model.
- **Report:** The thermal report includes `P_quantum_nW`, `P_classical_nW`, and `P_total_nW` so design can balance readout/control density against qubit coherence.
- **Thermal → decoherence:** Use `thermal_to_decoherence.py` to map the thermal report (and optional per-node power) to per-node gamma1/gamma2 for routing and open-system simulation.

## See also

- [CHANNEL_NOISE.md](CHANNEL_NOISE.md) — Kraus channels and noise injection in protocols.
- [engineering/thermodynamic_validator.py](../engineering/thermodynamic_validator.py) — π-baseline and 18 nW/cell compliance.
- [engineering/decoherence_rates.py](../engineering/decoherence_rates.py) — `get_node_decoherence_rates_from_file()`.
- [engineering/thermal_to_decoherence.py](../engineering/thermal_to_decoherence.py) — thermal report → decoherence file for routing/simulation.
