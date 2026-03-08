# QRNC: Quantum-Backed Tokens and BitCommit-Style Exchange

QRNC tokens are **quantum-backed** (minted from quantum entropy via the project's `QRNG.PY`). This package adds a **BitCommit-style two-party exchange**: commit then reveal, so neither party can change their token after seeing the other's.

## Protocol (two-party)

1. **Commit phase**: Alice and Bob each compute `H(token || nonce)` and exchange these commitments.
2. **Reveal phase**: Both send `(token, nonce)`. Each verifies the other's pair against the commitment.
3. **Completion**: If both verifications pass, the swap is complete; optionally an `ExchangeRecord` is produced for a ledger.

## Usage

```python
from qrnc import QRNC, mint_qrnc, run_two_party_exchange

# Mint tokens (quantum-backed; use_real_hardware=False for simulator)
token_a = mint_qrnc(num_bytes=32, use_real_hardware=False)
token_b = mint_qrnc(num_bytes=32, use_real_hardware=False)

# Or build from existing hex
token_a = QRNC.from_hex("a1b2c3...")
token_b = QRNC.from_hex("d4e5f6...")

# Run exchange (in-process)
received_by_a, received_by_b, record = run_two_party_exchange(
    token_a, token_b, party_a_id="Alice", party_b_id="Bob"
)
if received_by_a is not None:
    print("Exchange succeeded. Alice received:", received_by_b.value[:16], "...")
    # record can be appended to a ledger
```

Low-level commit/verify:

```python
from qrnc import commit, verify, generate_nonce

nonce = generate_nonce()
c = commit(token_bytes, nonce)
# ... send c to peer, later send (token_bytes, nonce) ...
ok = verify(c, token_bytes, nonce)
```

## Security caveats (exploratory)

- **No unconditional security**: Quantum bit commitment cannot be unconditionally secure (Mayers–Lo–Chau). This design uses a **classical** hash commitment for the exchange; the quantum part is token **generation** only.
- **Binding**: Hash-based commitment is computationally binding (collision resistance of SHA-256).
- **Hiding**: Hiding relies on sufficient entropy in token and nonce; nonce must be fresh and secret until reveal.
- **Scope**: No authentication, network layer, or replay protection in this iteration. The protocol only prevents one party from changing their token after seeing the other's; it does not protect against DoS or transport issues.

## Extension points

- **Ledger**: `ExchangeRecord` (party ids, commitments, timestamp, optional token hashes) is returned by `run_two_party_exchange`; a future `qrnc/ledger.py` can append it to a list or file.
- **Multi-party**: The same `commit` / `verify` primitives are party-agnostic and can be reused for multi-party or marketplace protocols.
