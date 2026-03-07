"""
Demo: Channel noise and decoherence on teleportation and tamper-evident link.
Runs teleport (and optionally thief) with configurable noise (depolarizing,
amplitude damping, phase damping) and reports fidelity. Compares environment-induced
vs tamper-induced fidelity drop.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
from state import State, ket0, ket1
from protocols.tamper_evident import run_thief_teleport
from protocols.noise import NoiseModel, run_teleport_with_noise, run_thief_with_noise


def main():
    print("=== Channel noise and decoherence demo ===\n")

    # Test message: superposition
    alpha = np.sqrt(0.7)
    beta = np.sqrt(0.3)
    msg = State(np.array([alpha, beta], dtype=np.complex128).reshape(-1, 1), 1)

    # --- Ideal teleport (no noise) ---
    # Fidelity reported is average over measurement outcomes (after Bob's correction).
    fid_ideal = run_teleport_with_noise(msg, NoiseModel())
    print(f"Teleport (no noise):     fidelity = {fid_ideal:.6f}  (ideal ~1.0; depends on state convention)")

    # --- Depolarizing on Bob's qubit after Bell creation ---
    noise_dep = NoiseModel().add("after_bell_creation", "depolarizing", [2], p=0.05)
    fid_dep = run_teleport_with_noise(msg, noise_dep)
    print(f"Teleport + depolarizing (p=0.05 on qubit 2): fidelity = {fid_dep:.6f}  (expect <= no-noise)")

    # --- Amplitude damping on Bob's qubit ---
    noise_amp = NoiseModel().add("after_bell_creation", "amplitude_damping", [2], gamma=0.1)
    fid_amp = run_teleport_with_noise(msg, noise_amp)
    print(f"Teleport + amplitude_damping (gamma=0.1 on qubit 2): fidelity = {fid_amp:.6f}")

    # --- Phase damping on Bob's qubit ---
    noise_phase = NoiseModel().add("after_bell_creation", "phase_damping", [2], lambda_p=0.15)
    fid_phase = run_teleport_with_noise(msg, noise_phase)
    print(f"Teleport + phase_damping (lambda=0.15 on qubit 2): fidelity = {fid_phase:.6f}")

    # --- Thief only (no channel noise) ---
    fid_thief = run_thief_with_noise(msg, thief_angle=0.5, noise_model=NoiseModel())
    print(f"Thief (Rx(0.5) on qubit 2, no channel noise): fidelity = {fid_thief:.6f}")

    # --- Thief + channel noise (environment + tampering) ---
    noise_both = NoiseModel().add("after_bell_creation", "depolarizing", [2], p=0.03)
    fid_thief_noise = run_thief_with_noise(msg, thief_angle=0.3, noise_model=noise_both)
    print(f"Thief (0.3) + depolarizing (p=0.03): fidelity = {fid_thief_noise:.6f}")

    # --- Compare: same fidelity drop from noise vs from thief? ---
    print("\n--- Environment vs tampering ---")
    print("Same message; compare fidelity drop from (a) noise only vs (b) thief only.")
    f_noise = run_teleport_with_noise(msg, noise_dep)
    f_thief_05 = run_thief_teleport(msg, thief_angle=0.5)
    print(f"  Depolarizing p=0.05:  fidelity = {f_noise:.6f}")
    print(f"  Thief angle=0.5:      fidelity = {f_thief_05:.6f}")
    print("  (Interpreting: similar drop can be due to environment or tampering;")
    print("   multiple probes or parameter sweeps help distinguish.)")

    print("\nNoise demo done. See docs/CHANNEL_NOISE.md for model formulas and usage.\n")


if __name__ == "__main__":
    main()
