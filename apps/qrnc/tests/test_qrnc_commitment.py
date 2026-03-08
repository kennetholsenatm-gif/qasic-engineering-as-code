"""
Unit tests for qrnc commitment primitive: commit, verify, nonce generation.
"""

import unittest
from qrnc.commitment import commit, verify, generate_nonce, reveal


class TestCommitment(unittest.TestCase):
    def test_commit_verify_roundtrip(self):
        token_value = b"token_value_here"
        nonce = generate_nonce()
        c = commit(token_value, nonce)
        self.assertTrue(verify(c, token_value, nonce))

    def test_verify_fails_wrong_nonce(self):
        token_value = b"token"
        nonce = generate_nonce()
        c = commit(token_value, nonce)
        wrong_nonce = generate_nonce()
        self.assertNotEqual(wrong_nonce, nonce)
        self.assertFalse(verify(c, token_value, wrong_nonce))

    def test_verify_fails_wrong_token(self):
        token_value = b"token"
        nonce = generate_nonce()
        c = commit(token_value, nonce)
        self.assertFalse(verify(c, b"other_token", nonce))

    def test_verify_fails_tampered_commitment(self):
        token_value = b"token"
        nonce = generate_nonce()
        c = commit(token_value, nonce)
        tampered = bytes([c[0] ^ 1] + list(c[1:]))
        self.assertFalse(verify(tampered, token_value, nonce))

    def test_commit_deterministic(self):
        token_value = b"same"
        nonce = b"fixed_nonce_32_bytes!!!!!!!!!!!!!!!!"
        c1 = commit(token_value, nonce)
        c2 = commit(token_value, nonce)
        self.assertEqual(c1, c2)

    def test_reveal_returns_tuple(self):
        token_value = b"token"
        nonce = b"nonce"
        r = reveal(token_value, nonce)
        self.assertEqual(r, (token_value, nonce))

    def test_nonce_fresh(self):
        n1 = generate_nonce()
        n2 = generate_nonce()
        self.assertNotEqual(n1, n2)


if __name__ == "__main__":
    unittest.main()
