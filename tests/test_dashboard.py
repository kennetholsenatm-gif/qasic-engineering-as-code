"""Smoke tests for CLI dashboard (import and menu helpers)."""
from __future__ import annotations

import pytest


def test_dashboard_import():
    from dashboard import cli_dashboard
    assert hasattr(cli_dashboard, "main")
    assert hasattr(cli_dashboard, "view_last_results")
    assert hasattr(cli_dashboard, "show_doc_links")


def test_dashboard_repo_root_resolved():
    from dashboard.cli_dashboard import REPO_ROOT, ENGINEERING_DIR
    assert REPO_ROOT.is_dir()
    assert (REPO_ROOT / "src" / "core_compute" / "engineering").exists()
    assert ENGINEERING_DIR == REPO_ROOT / "src" / "core_compute" / "engineering"
