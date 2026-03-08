# CI baseline for GDS / manifest diff

Store reference pipeline outputs here to compare against PR runs:

- `ci_result_geometry_manifest.json` — geometry manifest from a known-good run
- `ci_result_inverse_phases.npy` — optional phase array for phase summary diff

Update baseline on merge to main (e.g. copy from last successful run). The Hardware CI workflow uses `engineering/ci_gds_diff.py` to produce a diff report when these files exist.
