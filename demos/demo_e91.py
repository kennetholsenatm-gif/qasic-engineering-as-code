"""
Demo: E91 QKD (pedagogical). Bell pairs; Alice and Bob measure in random bases; CHSH and key.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from protocols.qkd import run_e91


def main() -> None:
    print("E91 QKD demo (Bell pairs + CHSH)\n")
    result = run_e91(n_trials=500, seed=42)
    print(f"  n_trials: {result['n_trials']}")
    print(f"  CHSH S: {result['chsh_s']:.4f} (quantum bound 2*sqrt(2) ~ 2.83)")
    print(f"  Key agreement: {result['key_agreement']}")
    print(f"  n_key (same basis): {result['n_key']}")
    print("\nDone.")


if __name__ == "__main__":
    main()
