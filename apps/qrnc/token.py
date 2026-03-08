"""
QRNC (quantum-backed) token type and issuance.

Uses QuantumRNG from the project's QRNG.PY for minting. Tokens are suitable
for use in the BitCommit-style exchange protocol.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import importlib.util
import sys
from typing import Optional

# Load QuantumRNG from qasic repo root QRNG.PY (when run from apps/qrnc/)
_project_root = Path(__file__).resolve().parent.parent.parent
_qrng_path = _project_root / "QRNG.PY"
QuantumRNG = None  # type: ignore
if _qrng_path.exists():
    _spec = importlib.util.spec_from_file_location("qrng_module", _qrng_path)
    if _spec is not None and _spec.loader is not None:
        if str(_project_root) not in sys.path:
            sys.path.insert(0, str(_project_root))
        _qrng_module = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_qrng_module)
        QuantumRNG = getattr(_qrng_module, "QuantumRNG", None)


@dataclass
class QRNC:
    """
    Quantum-backed token. Value is the hex string from quantum entropy;
    optional id and issued_at support future ledger use.
    """

    value: str
    id: Optional[str] = None
    issued_at: Optional[datetime] = None
    metadata: dict = field(default_factory=dict)

    def to_bytes(self) -> bytes:
        """Canonical bytes for commitment (hex decoded)."""
        return bytes.fromhex(self.value)

    @classmethod
    def from_hex(cls, value: str, id: Optional[str] = None, **kwargs) -> "QRNC":
        """Build a QRNC from an existing hex token string."""
        return cls(value=value, id=id, issued_at=datetime.now(timezone.utc), **kwargs)


def mint_qrnc(
    num_bytes: int = 32,
    use_real_hardware: bool = False,
    ibm_token: Optional[str] = None,
    token_id: Optional[str] = None,
) -> QRNC:
    """
    Mint a new QRNC token using quantum entropy from QuantumRNG.

    :param num_bytes: Length of the token in bytes (default 32).
    :param use_real_hardware: If True, use IBM Quantum hardware (requires ibm_token).
    :param ibm_token: IBM Quantum API token when use_real_hardware is True.
    :param token_id: Optional id for ledger/identification.
    :return: A new QRNC instance.
    """
    if QuantumRNG is None:
        raise RuntimeError("QRNG.PY not found; cannot mint quantum-backed tokens.")
    qrng = QuantumRNG(use_real_hardware=use_real_hardware, ibm_token=ibm_token)
    hex_value = qrng.generate_security_token(num_bytes=num_bytes)
    return QRNC.from_hex(hex_value, id=token_id)
