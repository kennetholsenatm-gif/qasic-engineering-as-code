"""
Demo: 3-qubit bit-flip repetition code on the Quantum ASIC (linear chain 0—1—2).
Encodes a logical bit, applies a single bit-flip error, corrects via syndrome, decodes.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from protocols.bitflip_code import run_bitflip_code


def main() -> None:
    print("3-qubit bit-flip repetition code (Quantum ASIC linear chain 0—1—2)\n")
    for logical in (0, 1):
        for err_q in (0, 1, 2):
            result = run_bitflip_code(logical, err_q)
            ok = "OK" if result["success"] else "FAIL"
            print(
                f"  Logical={logical}, error on qubit {err_q} -> syndrome {result['syndrome']}, "
                f"corrected q{result['corrected_qubit']}, decoded={result['decoded_bit']} [{ok}] "
                f"fidelity={result['fidelity']:.4f}"
            )
    print("\nDone.")


if __name__ == "__main__":
    main()
