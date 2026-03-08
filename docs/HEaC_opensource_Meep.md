# HEaC Open-Source Stack (Meep-Focused)

Short summary of the **Hardware-Engineering-as-Code (HEaC)** open-source tool chain for compiling software phase arrays into geometry, as in the [Automated HEaC whitepaper](Automated_HEaC_Deep_Cryogenic_Quantum_ASICs.tex). This path uses **Meep** (FDTD) for EM validation and optional **gdsfactory** for GDSII layout.

## Data flow

1. **Upstream:** Routing and inverse design produce `routing.json` and `phases.npy` (e.g. from `run_pipeline.py`).
2. **Meta-atom library:** A sweep over one geometric parameter (e.g. pillar width or loop radius) yields a table **(dimension → transmission phase)**. Done with Meep (real FDTD) or a deterministic formula when Meep is not installed.
3. **Interpolator:** From the library, build a mapping **phase φ → dimension d** (e.g. `scipy.interpolate.interp1d`).
4. **Phases → geometry manifest:** For each cell (i, j) in `phases.npy`, compute d = interpolator(φ_ij) and write a **geometry manifest** JSON: list of cells with `i`, `j`, `phase_rad`, `dimension`, plus pitch and units.
5. **Optional:** **Manifest → GDSII** via gdsfactory (place parameterized unit cells on a grid and export .gds).

## Tools (repository)

| Step | Script / module | Purpose |
|------|------------------|--------|
| Library | `engineering/heac/meep_unit_cell_sweep.py` | Sweep dimension → phase; output `meta_atom_library.json` (+ .npy). Meep or `--no-meep` synthetic. |
| Interpolator | `engineering/heac/phase_to_dimension.py` | Load library, build φ→d; CLI: `--table` for sample points. |
| Manifest | `engineering/heac/phases_to_geometry.py` | `phases.npy` + library → `geometry_manifest.json`. |
| GDS (optional) | `engineering/heac/manifest_to_gds.py` | Manifest → .gds (requires gdsfactory). Use `--pdk-config` for PDK layers and design rules. |
| DRC (optional) | `engineering/heac/run_drc_klayout.py` | Run DRC on GDS (KLayout batch or mock when KLayout not installed). |
| LVS (optional) | `engineering/heac/run_lvs_klayout.py` | Layout vs schematic: manifest + routing vs GDS (KLayout or mock). |
| Pipeline | `engineering/run_pipeline.py --heac` | After inverse design, run phases→manifest; create synthetic library if needed. Use `--gds --drc --lvs` for GDS + DRC/LVS. |

## Dependencies

- **Required for HEaC (manifest only):** `numpy`, `scipy` (interpolator).
- **Optional – Meep:** `pymeep` for real unit-cell FDTD sweep (otherwise synthetic library).
- **Optional – GDS:** `gdsfactory` for `manifest_to_gds.py`. PDK config: `engineering/heac/pdk_config.yaml` (minimal toy rules for CI; swap for foundry PDK for tape-out).
- **Optional – DRC/LVS:** KLayout on PATH for real DRC/LVS; otherwise mock mode (file checks) so CI passes.

See [engineering/README.md](../engineering/README.md#hardware-engineering-as-code-open-source-meep) for commands and [engineering/requirements-engineering.txt](../engineering/requirements-engineering.txt) for version notes.

## Geometry manifest format

The manifest JSON is the contract for downstream layout (gdsfactory, CadQuery, etc.):

- **Global:** `pitch_um`, `units`, `library_source`, `shape` [Ny, Nx], `num_cells`.
- **cells:** Array of `{ "i", "j", "phase_rad", "dimension" }` per cell.
