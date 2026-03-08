# Pedagogical QKD: BB84 and E91

This document describes the simplified QKD implementations in `protocols/qkd.py`. Both are **pedagogical** (no eavesdropper, perfect devices) for teaching and integration with the Quantum ASIC stack.

## BB84

- **Prepare-and-measure:** Alice sends random bits in the Z or X basis; Bob measures in a randomly chosen basis (Z or X).
- **Sifting:** Only rounds where bases match are kept. Half of the sifted bits form the raw key; the other half are used to estimate QBER (here 0, since there is no noise or eavesdropper).
- **Bases:** 0 = Z (computational), 1 = X (Hadamard).

## E91 (Ekert 91)

- **Entanglement-based:** A Bell pair is shared; Alice and Bob each choose one of three measurement bases.
- **Bases (simplified):** 0 = Z, 1 = X, 2 = same as 1 in this implementation (third basis approximated for pedagogy). In the full E91 protocol, Alice uses angles 0°, 45°, 90° and Bob 22.5°, 67.5° in the X–Z plane for the CHSH inequality.
- **CHSH:** \(S = E(0,0) - E(0,1) + E(1,0) + E(1,1)\). Classical \(|S| \leq 2\); quantum up to \(2\sqrt{2}\).
- **Key:** When Alice and Bob use the same basis, outcomes are perfectly correlated (or anticorrelated) for the Bell state; those outcomes form the key.

## Code

- `protocols/qkd.py`: `run_bb84(n_bits, seed)`, `run_e91(n_trials, seed)`.
- API: `POST /api/run/qkd` with body `{"protocol": "bb84"|"e91", "n_bits": 64, "n_trials": 500, "seed": null}`.
- Demos: `python demos/demo_bb84.py`, `python demos/demo_e91.py`.
