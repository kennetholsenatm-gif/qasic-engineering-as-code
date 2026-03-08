"""
Tests for two-party QRNC exchange protocol (in-process).
"""

import unittest
from qrnc import QRNC, run_two_party_exchange
from qrnc.exchange import ExchangeState


class TestExchange(unittest.TestCase):
    def test_exchange_success(self):
        token_a = QRNC.from_hex("a" * 64)
        token_b = QRNC.from_hex("b" * 64)
        received_by_a, received_by_b, record = run_two_party_exchange(
            token_a, token_b, party_a_id="Alice", party_b_id="Bob"
        )
        self.assertIsNotNone(received_by_a)
        self.assertIsNotNone(received_by_b)
        self.assertIsNotNone(record)
        self.assertEqual(received_by_a.value, token_b.value)
        self.assertEqual(received_by_b.value, token_a.value)
        self.assertEqual(record.party_a_id, "Alice")
        self.assertEqual(record.party_b_id, "Bob")
        self.assertNotEqual(record.commitment_a, record.commitment_b)
        self.assertIsNotNone(record.token_a_hash)
        self.assertIsNotNone(record.token_b_hash)

    def test_exchange_fails_if_one_cheats_reveal(self):
        token_a = QRNC.from_hex("a" * 64)
        token_b = QRNC.from_hex("b" * 64)
        state_a = ExchangeState.create(token_a)
        state_b = ExchangeState.create(token_b)

        state_a.set_peer_commitment(state_b.get_commitment())
        state_b.set_peer_commitment(state_a.get_commitment())

        state_a.set_peer_reveal(token_b.to_bytes(), state_b.my_nonce)
        state_b.set_peer_reveal(b"wrong_token_value!!!!!!!", state_a.my_nonce)

        self.assertTrue(state_a.verify_peer())
        self.assertFalse(state_b.verify_peer())

    def test_exchange_record_has_timestamp(self):
        token_a = QRNC.from_hex("c" * 64)
        token_b = QRNC.from_hex("d" * 64)
        _, _, record = run_two_party_exchange(token_a, token_b)
        self.assertIsNotNone(record)
        self.assertIsNotNone(record.timestamp)


if __name__ == "__main__":
    unittest.main()
