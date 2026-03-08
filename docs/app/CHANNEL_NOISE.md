# Channel Noise and Decoherence Simulator

This document describes the **noise channel models** and how to use them with the teleport and tamper-evident protocols. The simulator bridges the "perfect devices" assumption toward **weather-resilient SATCOM** by injecting realistic noise (atmospheric attenuation, thermal fluctuations, detector inefficiency) and reporting fidelity.

## Density-matrix path (exact expectation values)

The recommended integration is the **density-matrix path** (no sampling):

- **State representation:** ρ as a 2^n×2^n matrix (`DensityState` or `state_to_density(State)`).
- **Channel application:** Each channel is applied as ρ → Σ_i K_i ρ K_i† (Kraus sum). Implemented in `state/channels.py` via `apply_single_qubit_channel(rho, qubit, kraus_ops, n_qubits)`.
- **Fidelity:** For mixed ρ and target pure |ψ⟩, F = ⟨ψ|ρ|ψ⟩. Implemented as `fidelity_pure_vs_density(target_pure, rho)` in `state/density.py`.

This gives **exact average fidelity** over the noise (no quantum trajectory sampling). The protocol layer runs the circuit in density form, applies noise at the configured steps, then computes F for Bob’s reduced state after correction.

## Noise models

All channels are implemented as **Kraus operators** and applied to density matrices. Single-qubit channels can be applied to any qubit of an n-qubit state.

| Channel | Parameter(s) | Description |
|--------|---------------|-------------|
| **Depolarizing** | `p` ∈ [0, 1] | With probability p, apply X, Y, or Z uniformly; with 1−p identity. Standard generic qubit error. |
| **Amplitude damping** | `gamma` ∈ [0, 1] | T1-like: \|1⟩ → \|0⟩ with probability gamma. Map to T1 via γ = 1 − exp(−t/T1). |
| **Phase damping** | `lambda` ∈ [0, 1] | T2-like: decays off-diagonal coherence. |
| **Thermal** | `p_ex` ∈ [0, 1] | Full replacement with thermal state (1−p_ex)\|0⟩⟨0\| + p_ex\|1⟩⟨1\|. |
| **Thermal loss** | `eta` ∈ [0, 1] | E(ρ) = η ρ + (1−η) I/2. With probability η state unchanged; with 1−η replaced by maximally mixed (thermal background). Used in **DV Quantum Illumination**. |
| **Detector loss** | `eta` ∈ [0, 1] | Efficiency eta; with probability 1−eta the qubit is lost (amplitude damping with γ = 1−eta). |

## Usage

### State and channels

- **`state/channels.py`**: Kraus operators (`kraus_depolarizing`, `kraus_amplitude_damping`, etc.) and `apply_single_qubit_channel(rho, qubit, kraus_ops, n_qubits)`.
- **`state/density.py`**: `DensityState`, `state_to_density`, `density_to_state`, `fidelity_pure_vs_density` for exact average fidelity without sampling.

### Protocol-level API

- **`protocols/noise.py`**:
  - **`NoiseModel()`**: Add injections with `.add(when, channel, qubits, **kwargs)`.
  - **`when`**: Step index (int) or name: `"after_bell_creation"`, `"after_alice"`, `"before_readout"`.
  - **`run_teleport_with_noise(msg_state, noise_model)`**: Returns average fidelity of Bob’s state (after measurement and correction) to the message.
  - **`run_thief_with_noise(msg_state, thief_angle, noise_model)`**: Tamper (Rx on Bob’s qubit) plus optional channel noise.

Qubit labels in the noise model are **protocol order**: 0 = message, 1 = Alice, 2 = Bob. They are mapped internally to the state index convention.

### Example

```python
from state import State
from protocols.noise import NoiseModel, run_teleport_with_noise

msg = State(np.array([0.6, 0.8], dtype=complex).reshape(-1, 1), 1)
noise = NoiseModel().add("after_bell_creation", "depolarizing", [2], p=0.05)
fidelity = run_teleport_with_noise(msg, noise)
```

## Interpreting fidelity

- **No noise**: Fidelity depends on the state-index convention and correction; the demo reports the average fidelity over measurement outcomes after Bob’s correction.
- **With noise**: Fidelity drops; compare e.g. depolarizing vs amplitude damping to see different degradation.
- **Thief vs environment**: A similar fidelity drop can come from tampering (Thief’s Rx) or from channel noise; multiple probes or parameter sweeps help distinguish.

## DV Quantum Illumination (toy)

A **Discrete Variable** toy analogue of Seth Lloyd’s Quantum Illumination (2008): use a Bell pair (Idler, Signal); the Signal is either reflected (H1, with probability η unchanged, else replaced by thermal I/2) or lost (H0, receiver gets I/2). A joint Bell-basis measurement on (Idler, Return) distinguishes H0 vs H1 with lower error probability than sending a single unentangled photon.

- **Channel:** Thermal loss `thermal_loss(rho, qubit, eta)` implements E(ρ) = η ρ + (1−η) I/2.
- **Protocol:** `protocols/quantum_illumination.py` — `rho_H1(eta)`, `rho_H0()`, `entangled_probe_metrics(eta)`, `unentangled_probe_metrics(eta)`, `run_comparison(eta)`.
- **Run:** `python protocols/quantum_illumination.py --eta 0.1` to print P_err and Chernoff exponent for entangled vs unentangled probe.

## Files

- `state/channels.py` — Kraus operators (including `kraus_thermal_loss`, `thermal_loss`) and application to density matrices.
- `state/density.py` — DensityState, `apply_channel`, and conversion to/from State.
- `protocols/noise.py` — NoiseModel, injection points, run_teleport_with_noise, run_thief_with_noise.
- `protocols/quantum_illumination.py` — DV Quantum Illumination: Bell probe vs unentangled |1⟩, error and Chernoff comparison.
- `demos/demo_noise.py` — Run teleport and tamper with configurable noise.

## Run the demo

```bash
python demos/demo_noise.py
```

For **layout-aware decoherence** (parasitic extraction from geometry manifest) and **thermal stage reports** (10 mK / 4 K / 50 K), see [THERMAL_AND_PARASITICS.md](THERMAL_AND_PARASITICS.md). See also the whitepaper (§ SATCOM, thermal noise, radiative cooling) and the repository README.
