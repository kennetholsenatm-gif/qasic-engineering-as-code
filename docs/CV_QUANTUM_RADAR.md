# Toy CV Quantum Radar (TMSV + Covariance Matrices)

Physics-accurate **continuous-variable** simulation matching the whitepaper's TMSV description: Gaussian states via covariance matrices, symplectic operations (squeezing, beam splitter), and metrics for the (idler, return) state after a lossy thermal channel.

## Why CV and covariance matrices

- **Qubits** are not enough for true microwave photons and phased arrays; the whitepaper describes **two-mode squeezed vacuum (TMSV)** and thermal baths.
- A full framework like Strawberry Fields is not required: radar uses **Gaussian states and Gaussian operations**, which are fully described by a **mean vector** \(\mathbf{d}\) and **covariance matrix** \(\mathbf{V}\) (2N×2N for N modes).
- Operations are **symplectic**: \(V' = S V S^T\). No need for large Hilbert spaces.

## State representation

- **`state/cv_state.py`**: `GaussianState(V, d, n_modes)` with covariance `V` (2N×2N real, symmetric) and optional mean `d` (2N). Quadrature order: \((q_1, p_1, q_2, p_2, \ldots)\). Vacuum: \(V = I/2\) per mode (ℏ=1).
- **Symplectic form** \(\Omega\): block-diagonal with \(J = \begin{pmatrix} 0 & 1 \\ -1 & 0 \end{pmatrix}\) per mode.
- **Helpers**: `vacuum_covariance(n_modes)`, `thermal_covariance(n_bar)` (single-mode thermal), `apply_symplectic(S)`, `reduced(modes)`, `symplectic_eigenvalues()`, `von_neumann_entropy()`.

## Gates (symplectic matrices)

- **`state/cv_gates.py`**:
  - **Two-mode squeezing** \(S(r)\): generates TMSV from vacuum; applied as \(V' = S V S^T\).
  - **Beam splitter** \(B(T)\): transmittance \(T\); mixes two modes (e.g. signal with thermal bath).
  - **TMSV covariance** `tmsv_covariance(r)`: direct 4×4 covariance of two-mode squeezed vacuum.

## Protocol: quantum radar

- **`protocols/quantum_radar.py`**:
  1. **TMSV** on modes 0 (idler) and 1 (signal) with squeezing \(r\).
  2. Mode 2 = thermal bath (mean photon number \(N_B\)).
  3. **Beam splitter** on modes 1 and 2 with **transmittance** \(\eta\) (signal survival probability).
  4. **Return** = reduced state on modes 0 and 1 (idler + return mode).

- **H1 (target present)**: \(\eta > 0\); (idler, return) are correlated.
- **H0 (target absent)**: \(\eta = 0\); return is thermal \(N_B\), idler is reduced TMSV (thermal), no correlation.

**Metrics**:
- **Mutual information** \(I(\text{idler}; \text{return})\): \(S(V_A) + S(V_B) - S(V_{AB})\).
- **Return variance** and **SNR proxy** (inverse variance) for homodyne-style detection.

## Usage

**Single run:**
```bash
python protocols/quantum_radar.py --eta 0.1 --n_b 10 --r 0.5
```

**Sweep** one parameter (eta, n_b, or r) over a range; others fixed via `--eta`, `--n_b`, `--r`:
```bash
python protocols/quantum_radar.py --sweep r --min 0.2 --max 1.2 --steps 21 --eta 0.2 --n_b 2
python protocols/quantum_radar.py --sweep eta --min 0.05 --max 0.5 --steps 11 --n_b 2 --r 1 -o sweep.csv
```
Use `--min` / `--max` to set the sweep range (defaults: eta [0.01, 0.5], n_b [0.1, 50], r [0.1, 1.5]). Optional `-o file.csv` writes the table to CSV.

**Optimize** one parameter by grid search (maximize `mutual_info_H1` or `snr_proxy_H1`):
```bash
python protocols/quantum_radar.py --optimize r --eta 0.2 --n_b 2 --maximize mutual_info --steps 50
python protocols/quantum_radar.py --optimize r --eta 0.2 --n_b 2 --maximize snr --optimize-min 0.1 --optimize-max 1.5
```
Use `--optimize-min` / `--optimize-max` to set the search range (defaults: eta [0.01, 0.99], n_b [0, 100], r [0.05, 2]).

**From Python:**
```python
from protocols.quantum_radar import tmsv_through_loss, run_quantum_radar, mutual_information, sweep_parameter, optimize_parameter

state = tmsv_through_loss(eta=0.1, n_b=10.0, r=0.5)
I = mutual_information(state)
out = run_quantum_radar(eta=0.01, n_b=100, r=0.5)
# Sweep
rows = sweep_parameter("r", 0.2, 1.2, 21, eta=0.2, n_b=2.0, r=0.5)
# Optimize (best value, best result dict)
best_r, best = optimize_parameter("r", 0.1, 2.0, 50, eta=0.2, n_b=2.0, r=0.5, maximize="mutual_info")
```

## Files

- `state/cv_state.py` — `GaussianState`, symplectic form, reduced state, symplectic eigenvalues, entropy.
- `state/cv_gates.py` — `two_mode_squeezing(r)`, `beam_splitter(transmittance)`, `tmsv_covariance(r)`.
- `protocols/quantum_radar.py` — TMSV through lossy thermal BS, H0/H1 states, mutual information, SNR proxy.

## Relation to whitepaper

The whitepaper describes microwave quantum illumination with TMSV, thermal clutter, and joint measurement for improved Chernoff exponent. This toy implements the **Gaussian (covariance)** part only: TMSV generation, loss and mixing with thermal bath via beam splitter, and information-theoretic metrics (mutual information, variance). Homodyne/heterodyne detection and error exponents can be extended from the output covariance matrices.
