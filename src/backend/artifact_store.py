"""
Artifact store: put/get files by URI so DAG nodes can pass outputs across workers (local, S3).
Interface: put(run_id, key, local_path) -> uri; get(uri) -> local_path; get_optional(uri) -> local_path | None.
"""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote

REPO_ROOT = Path(__file__).resolve().parents[2]
import sys
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Default: local file store under storage/artifacts
DEFAULT_ARTIFACT_BASE = REPO_ROOT / "storage" / "artifacts"


def _get_artifact_base() -> Path:
    base = os.environ.get("QASIC_ARTIFACT_STORE_BASE", "").strip()
    if base:
        return Path(base)
    try:
        from config import get_app_config
        path = getattr(get_app_config().paths, "artifact_store_base", None)
        if path:
            return Path(path)
    except Exception:
        pass
    return DEFAULT_ARTIFACT_BASE


def _local_put(run_id: int, key: str, local_path: str | Path) -> str:
    """Store file at base/run_id/key; return file:// URI."""
    base = _get_artifact_base()
    dest_dir = base / str(run_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    # key may contain slashes; use a safe filename
    safe_key = quote(key, safe="")
    dest = dest_dir / safe_key
    shutil.copy2(str(local_path), str(dest))
    return f"file://{dest.resolve().as_posix()}"


def _local_get(uri: str) -> Path:
    """Download file:// URI to a local path (return path; for file:// just return path)."""
    if not uri.startswith("file://"):
        raise ValueError(f"Unsupported artifact URI: {uri}")
    path = Path(unquote(uri.removeprefix("file://")))
    if not path.is_file():
        raise FileNotFoundError(uri)
    return path


def _local_get_optional(uri: str) -> Path | None:
    try:
        return _local_get(uri)
    except FileNotFoundError:
        return None


def put(run_id: int, key: str, local_path: str | Path) -> str:
    """Store the file at local_path for run_id/key. Returns URI (file:// or s3://)."""
    backend = os.environ.get("QASIC_ARTIFACT_STORE_BACKEND", "local").strip().lower()
    if backend == "s3":
        return _s3_put(run_id, key, local_path)
    return _local_put(run_id, key, local_path)


def get(uri: str) -> Path:
    """Resolve URI to a local path (download to temp if needed). Returns path."""
    if uri.startswith("file://"):
        return _local_get(uri)
    if uri.startswith("s3://"):
        return _s3_get(uri)
    raise ValueError(f"Unsupported artifact URI: {uri}")


def get_optional(uri: str) -> Path | None:
    """Like get() but returns None if the artifact is missing."""
    try:
        return get(uri)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def _s3_put(run_id: int, key: str, local_path: str | Path) -> str:
    """Upload to S3; return s3:// URI. Requires boto3 and env/config."""
    try:
        import boto3
        bucket = os.environ.get("QASIC_ARTIFACT_S3_BUCKET", "").strip()
        if not bucket:
            raise ValueError("QASIC_ARTIFACT_S3_BUCKET not set")
        prefix = os.environ.get("QASIC_ARTIFACT_S3_PREFIX", "qasic-artifacts").strip()
        s3_key = f"{prefix}/{run_id}/{quote(key, safe='')}"
        boto3.Session().client("s3").upload_file(str(local_path), bucket, s3_key)
        return f"s3://{bucket}/{s3_key}"
    except ImportError:
        raise ValueError("S3 artifact store requires boto3")
    except Exception as e:
        raise RuntimeError(f"S3 put failed: {e}") from e


def _s3_get(uri: str) -> Path:
    """Download s3:// URI to temp file; return path."""
    try:
        import boto3
        from urllib.parse import urlparse
        p = urlparse(uri)
        if p.scheme != "s3" or not p.netloc or not p.path.lstrip("/"):
            raise ValueError(f"Invalid S3 URI: {uri}")
        bucket = p.netloc
        key = p.path.lstrip("/")
        fd, path = tempfile.mkstemp(suffix=Path(key).suffix or "")
        os.close(fd)
        boto3.Session().client("s3").download_file(bucket, key, path)
        return Path(path)
    except ImportError:
        raise ValueError("S3 artifact store requires boto3")
    except Exception as e:
        raise RuntimeError(f"S3 get failed: {e}") from e


def resolve_input_to_path(value: Any) -> Any:
    """If value is a string URI (file:// or s3://), return local Path; else return value."""
    if isinstance(value, str) and (value.startswith("file://") or value.startswith("s3://")):
        return get(value)
    return value


def store_outputs_as_uris(run_id: int, outputs: dict[str, Any]) -> dict[str, Any]:
    """For each output value that is an existing file path, replace with put() URI."""
    result = {}
    for k, v in outputs.items():
        if isinstance(v, str) and os.path.isfile(v):
            result[k] = put(run_id, k, v)
        else:
            result[k] = v
    return result
