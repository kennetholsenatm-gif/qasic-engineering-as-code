"""Smoke tests for FastAPI app (routes and health). Requires: pip install -r app/requirements.txt"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_docs_links(client):
    r = client.get("/api/docs/links")
    assert r.status_code == 200
    data = r.json()
    assert "links" in data
    assert isinstance(data["links"], list)


def test_results_latest(client):
    r = client.get("/api/results/latest")
    assert r.status_code == 200
    data = r.json()
    assert "routing_path" in data
    assert "inverse_path" in data


def test_docs_serve_allowed(client):
    """Serve an allowed doc file (docs/README.md) returns 200 and markdown content."""
    r = client.get("/docs/docs/README.md")
    assert r.status_code == 200
    assert "text/markdown" in r.headers.get("content-type", "")
    assert len(r.content) > 0


def test_docs_serve_disallowed_404(client):
    """Disallowed or non-existent doc path returns 404."""
    r = client.get("/docs/unknown/path.md")
    assert r.status_code == 404
