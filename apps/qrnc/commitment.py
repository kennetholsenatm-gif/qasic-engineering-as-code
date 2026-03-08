"""
Bit-commitment primitive (classical hash-based).

Commit phase: lock a value without revealing it (binding, hiding).
Reveal phase: send (value, nonce); receiver verifies against commitment.

This is a classical commitment; the "quantum" aspect is token generation
in qrnc.token. Optional future: quantum commitment protocol.
"""

import hashlib
import secrets
from typing import Tuple


def generate_nonce(size_bytes: int = 32) -> bytes:
    """
    Generate a fresh nonce for commitment. Uses stdlib secrets (crypto-grade).
    Nonce must be kept secret until reveal and used only once.
    """
    return secrets.token_bytes(size_bytes)


def commit(token_value: bytes, nonce: bytes) -> bytes:
    """
    Produce a commitment to token_value using nonce.
    H(token_value || nonce) with SHA-256. Binding and hiding under standard assumptions.
    """
    h = hashlib.sha256()
    h.update(token_value)
    h.update(nonce)
    return h.digest()


def reveal(token_value: bytes, nonce: bytes) -> Tuple[bytes, bytes]:
    """
    Reveal data: the pair (token_value, nonce) to be sent to the verifier.
    Pass-through; the actual "reveal" is sending this pair.
    """
    return (token_value, nonce)


def verify(commitment: bytes, token_value: bytes, nonce: bytes) -> bool:
    """
    Verify that (token_value, nonce) matches the earlier commitment.
    Returns True iff commit(token_value, nonce) == commitment.
    """
    return commit(token_value, nonce) == commitment
