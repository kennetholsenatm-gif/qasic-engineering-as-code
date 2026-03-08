"""
Pytest configuration: add repo root to sys.path so tests can import src.backend, src.core_compute.*.
Run from repo root: pytest tests/
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
