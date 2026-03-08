"""
Demo: BB84 QKD (pedagogical). Alice sends random bits in Z or X basis; Bob measures; sift and QBER.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from protocols.qkd import run_bb84


def main() -> None:
    print("BB84 QKD demo (no eavesdropper)\n")
    result = run_bb84(n_bits=256, seed=42)
    print(f"  n_bits sent: {result['n_bits']}")
    print(f"  n_sift (same basis): {result['n_sift']}")
    print(f"  QBER (test half): {result['qber']:.4f}")
    print(f"  Key agreement: {result['key_agreement']}")
    if result["key_bits"][0]:
        print(f"  Key length: {len(result['key_bits'][0])} bits")
    print("\nDone.")


if __name__ == "__main__":
    main()
