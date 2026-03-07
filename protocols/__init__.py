# Toy quantum protocols: teleportation, tamper-evidence, bit commitment, noise.
from .entanglement import create_bell_pair, distribute_pairs
from .teleportation import teleport, teleport_circuit
from .tamper_evident import run_legitimate_teleport, run_thief_teleport, fidelity_after_thief
from .commitment import commit, open_commitment, verify_commitment
from .noise import NoiseModel, run_teleport_with_noise, run_thief_with_noise
from .quantum_illumination import (
    rho_H0,
    rho_H1,
    entangled_probe_metrics,
    unentangled_probe_metrics,
    run_comparison,
)
from .quantum_radar import (
    tmsv_through_loss,
    state_H0_target_absent,
    mutual_information,
    run_quantum_radar,
    sweep_parameter,
    optimize_parameter,
)

__all__ = [
    "create_bell_pair",
    "distribute_pairs",
    "teleport",
    "teleport_circuit",
    "run_legitimate_teleport",
    "run_thief_teleport",
    "fidelity_after_thief",
    "commit",
    "open_commitment",
    "verify_commitment",
    "NoiseModel",
    "run_teleport_with_noise",
    "run_thief_with_noise",
    "rho_H0",
    "rho_H1",
    "entangled_probe_metrics",
    "unentangled_probe_metrics",
    "run_comparison",
    "tmsv_through_loss",
    "state_H0_target_absent",
    "mutual_information",
    "run_quantum_radar",
    "sweep_parameter",
    "optimize_parameter",
]
