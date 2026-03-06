"""
Demo: tamper-evidence. When a Thief disturbs Bob's qubit during teleportation,
fidelity drops. The receiver can detect the interference.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
from state import State, ket0, ket1
from protocols.tamper_evident import run_legitimate_teleport, run_thief_teleport, fidelity_after_thief


def main():
    print("=== Tamper-evidence demo (Thief) ===\n")

    msg = State(np.array([0.6, 0.8], dtype=np.complex128).reshape(-1, 1), 1)  # already normalized

    f_legit = run_legitimate_teleport(msg)
    print(f"  Legitimate teleport fidelity: {f_legit:.6f}  (expect 1.0)")

    for angle in [0.1, 0.3, 0.5, 1.0]:
        f = run_thief_teleport(msg, thief_angle=angle)
        print(f"  With Thief (Rx({angle}) on Bob's qubit): fidelity = {f:.6f}")

    print("\nInterference is detectable: fidelity drops when the channel is disturbed.\n")


if __name__ == "__main__":
    main()
