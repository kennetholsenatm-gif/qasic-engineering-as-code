"""
Two-party QRNC exchange protocol using BitCommit-style commit-then-reveal.

Commit phase: each party sends H(token || nonce). Reveal phase: both send
(token, nonce); each verifies the other. On success, exchange is binding and fair.
Does not protect against DoS or network issues—only against changing one's token
after seeing the other's.
"""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Tuple

from .commitment import commit, verify, generate_nonce, reveal
from .token import QRNC


@dataclass
class ExchangeRecord:
    """
    Minimal exchange record for ledger extension.
    A future qrnc/ledger.py can append this to a list or file.
    """

    party_a_id: str
    party_b_id: str
    commitment_a: bytes
    commitment_b: bytes
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    token_a_hash: Optional[bytes] = None  # optional hash of revealed token A
    token_b_hash: Optional[bytes] = None  # optional hash of revealed token B


@dataclass
class ExchangeState:
    """
    One party's state during the exchange (committer/revealer).
    """

    my_token: QRNC
    my_nonce: bytes
    my_commitment: bytes
    peer_commitment: Optional[bytes] = None
    peer_token_value: Optional[bytes] = None
    peer_nonce: Optional[bytes] = None
    peer_id: str = ""

    @classmethod
    def create(cls, token: QRNC, nonce: Optional[bytes] = None) -> "ExchangeState":
        nonce = nonce or generate_nonce()
        token_bytes = token.to_bytes()
        return cls(
            my_token=token,
            my_nonce=nonce,
            my_commitment=commit(token_bytes, nonce),
        )

    def get_commitment(self) -> bytes:
        return self.my_commitment

    def set_peer_commitment(self, commitment: bytes, peer_id: str = "") -> None:
        self.peer_commitment = commitment
        self.peer_id = peer_id

    def get_reveal(self) -> Tuple[bytes, bytes]:
        return reveal(self.my_token.to_bytes(), self.my_nonce)

    def set_peer_reveal(self, token_value: bytes, nonce: bytes) -> None:
        self.peer_token_value = token_value
        self.peer_nonce = nonce

    def verify_peer(self) -> bool:
        if self.peer_commitment is None or self.peer_token_value is None or self.peer_nonce is None:
            return False
        return verify(self.peer_commitment, self.peer_token_value, self.peer_nonce)

    def get_peer_token_hex(self) -> str:
        if self.peer_token_value is None:
            raise ValueError("Peer not yet revealed")
        return self.peer_token_value.hex()


def run_two_party_exchange(
    token_a: QRNC,
    token_b: QRNC,
    party_a_id: str = "A",
    party_b_id: str = "B",
) -> Tuple[Optional[QRNC], Optional[QRNC], Optional[ExchangeRecord]]:
    """
    Run the full commit-then-reveal exchange in-process (Alice and Bob in one process).
    Returns (token_received_by_a, token_received_by_b, exchange_record_or_none).
    On verification failure, returns (None, None, None); no token transfer.
    """

    state_a = ExchangeState.create(token_a)
    state_b = ExchangeState.create(token_b)

    # Commit phase: exchange commitments
    state_a.set_peer_commitment(state_b.get_commitment(), peer_id=party_b_id)
    state_b.set_peer_commitment(state_a.get_commitment(), peer_id=party_a_id)

    # Reveal phase: exchange (token_value, nonce)
    reveal_a = state_a.get_reveal()
    reveal_b = state_b.get_reveal()
    state_a.set_peer_reveal(reveal_b[0], reveal_b[1])
    state_b.set_peer_reveal(reveal_a[0], reveal_a[1])

    # Verify
    if not state_a.verify_peer() or not state_b.verify_peer():
        return (None, None, None)

    # Completion: each party accepts the other's token
    token_received_by_a = QRNC.from_hex(state_a.get_peer_token_hex())
    token_received_by_b = QRNC.from_hex(state_b.get_peer_token_hex())

    record = ExchangeRecord(
        party_a_id=party_a_id,
        party_b_id=party_b_id,
        commitment_a=state_a.my_commitment,
        commitment_b=state_b.my_commitment,
        token_a_hash=hashlib.sha256(token_a.to_bytes()).digest(),
        token_b_hash=hashlib.sha256(token_b.to_bytes()).digest(),
    )

    return (token_received_by_a, token_received_by_b, record)
