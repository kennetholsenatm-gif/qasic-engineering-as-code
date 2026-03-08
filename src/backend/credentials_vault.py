"""
Secure credentials vault: read/write a JSON file (e.g. in container storage).
Used for IBM Quantum token and other API keys entered via the Workflow UI.
Never log or return raw secret values.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# Known keys we allow in the vault (do not store arbitrary keys to avoid abuse)
ALLOWED_KEYS = frozenset({"ibm_quantum_token", "aws_access_key_id", "aws_secret_access_key"})
MAX_PAYLOAD_BYTES = 16 * 1024  # 16KB total


def _get_vault_path(credentials_file: str, repo_root: Path) -> Path | None:
    """Resolve vault file path. If empty, use default under storage/."""
    path = (credentials_file or "").strip()
    if path:
        return Path(path)
    return repo_root / "storage" / "credentials.json"


def _get_source_path(repo_root: Path) -> Path:
    """Path to the small file that stores credentials_source and credentials_path."""
    return repo_root / "storage" / "credentials_source.json"


def _read_credentials_source(repo_root: Path) -> tuple[str, str]:
    """Return (credentials_source, credentials_path). source is 'vault' or 'file'."""
    p = _get_source_path(repo_root)
    if not p.is_file():
        return ("vault", "")
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return ("vault", "")
    src = data.get("credentials_source") or "vault"
    path = (data.get("credentials_path") or "").strip()
    if src != "file":
        path = ""
    return (src, path)


def _write_credentials_source(repo_root: Path, credentials_source: str, credentials_path: str) -> None:
    """Persist credentials source and path (for 'Use external file')."""
    p = _get_source_path(repo_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"credentials_source": credentials_source, "credentials_path": credentials_path}, f)
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass


def _read_json_file(p: Path) -> dict[str, Any]:
    """Read JSON file; return dict of allowed keys only."""
    if not p or not p.is_file():
        return {}
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: v for k, v in data.items() if k in ALLOWED_KEYS and isinstance(v, str)}


def read_vault(credentials_file: str, repo_root: Path) -> dict[str, Any]:
    """Read credentials from vault or from external path. Returns dict of key -> value. Never log values."""
    source, ext_path = _read_credentials_source(repo_root)
    if source == "file" and ext_path:
        return _read_json_file(Path(ext_path))
    p = _get_vault_path(credentials_file, repo_root)
    return _read_json_file(p) if p else {}


def write_vault(credentials_file: str, repo_root: Path, payload: dict[str, Any]) -> None:
    """Write vault JSON. Only allowed keys; chmod 0o600. Raises on error."""
    if len(json.dumps(payload)) > MAX_PAYLOAD_BYTES:
        raise ValueError("Credentials payload too large")
    allowed = {k: v for k, v in payload.items() if k in ALLOWED_KEYS and isinstance(v, str)}
    p = _get_vault_path(credentials_file, repo_root)
    if not p:
        raise ValueError("No credentials file path configured")
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(allowed, f, indent=0)
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass


def get_credentials_status(credentials_file: str, repo_root: Path) -> dict[str, Any]:
    """Return status only: which keys are configured, no values. Includes credentials_source and credentials_path."""
    source, ext_path = _read_credentials_source(repo_root)
    data = read_vault(credentials_file, repo_root)
    out = {
        "ibm_quantum_token_configured": bool(data.get("ibm_quantum_token")),
        "aws_access_key_id_configured": bool(data.get("aws_access_key_id")),
        "aws_secret_access_key_configured": bool(data.get("aws_secret_access_key")),
        "credentials_source": source,
    }
    if source == "file" and ext_path:
        out["credentials_path"] = ext_path
    return out


def set_credentials_source(repo_root: Path, credentials_source: str, credentials_path: str) -> None:
    """Set credentials source to 'vault' or 'file' and optional path. For 'file', path is required."""
    if credentials_source == "file" and not (credentials_path or "").strip():
        raise ValueError("credentials_path is required when credentials_source is 'file'")
    _write_credentials_source(repo_root, credentials_source, (credentials_path or "").strip())


def load_credentials_into_env(credentials_file: str, repo_root: Path) -> None:
    """Load vault credentials into os.environ for the current process. Used by Celery tasks."""
    data = read_vault(credentials_file, repo_root)
    if data.get("ibm_quantum_token") and "IBM_QUANTUM_TOKEN" not in os.environ:
        os.environ["IBM_QUANTUM_TOKEN"] = data["ibm_quantum_token"]
    if data.get("aws_access_key_id") and "AWS_ACCESS_KEY_ID" not in os.environ:
        os.environ["AWS_ACCESS_KEY_ID"] = data["aws_access_key_id"]
    if data.get("aws_secret_access_key") and "AWS_SECRET_ACCESS_KEY" not in os.environ:
        os.environ["AWS_SECRET_ACCESS_KEY"] = data["aws_secret_access_key"]
