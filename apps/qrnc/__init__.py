"""
QRNC: quantum-backed tokens and BitCommit-style two-party exchange.

- QRNC tokens are minted using quantum entropy (QRNG.PY).
- Exchange uses commit-then-reveal (classical hash commitment) for fair swaps.
- Security is exploratory; no unconditional guarantees (see README).
"""

from .token import QRNC, mint_qrnc
from .commitment import commit, verify, generate_nonce, reveal
from .exchange import (
    ExchangeState,
    ExchangeRecord,
    run_two_party_exchange,
)

__all__ = [
    "QRNC",
    "mint_qrnc",
    "commit",
    "verify",
    "generate_nonce",
    "reveal",
    "ExchangeState",
    "ExchangeRecord",
    "run_two_party_exchange",
]
