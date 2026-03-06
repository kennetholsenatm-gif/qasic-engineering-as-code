"""
Demo: toy bit commitment. Alice commits to a bit using shared entanglement;
she opens by revealing the bit and classical data. Bob verifies consistency.
(Toy: security under passive adversary / no quantum storage.)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from protocols.commitment import run_commitment_protocol


def main():
    print("=== Toy bit commitment demo ===\n")

    for bit in [0, 1]:
        result = run_commitment_protocol(bit, seed=bit * 100)
        print(f"  Commit to {bit}: (b={result['committed_bit']}, m={result['measurement_m']})")
        print(f"    Bob's outcome: {result['bob_outcome']}, verify_ok: {result['verify_ok']}")

    print("\nBinding: Alice cannot change b after measuring (no quantum copy).")
    print("Hiding: Bob's reduced state is I/2 until open (no info about b).\n")


if __name__ == "__main__":
    main()
