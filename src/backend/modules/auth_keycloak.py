"""
Keycloak auth integration: exposes config for the frontend when FEATURE_KEYCLOAK_ENABLED is set.
OpenTofu/Helm inject KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_CLIENT_ID into the API container.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException

keycloak_router = APIRouter()

KEYCLOAK_URL = os.environ.get("KEYCLOAK_URL", "").strip()
KEYCLOAK_REALM = os.environ.get("KEYCLOAK_REALM", "qasic")
KEYCLOAK_CLIENT_ID = os.environ.get("KEYCLOAK_CLIENT_ID", "qasic-frontend")


@keycloak_router.get("/config")
def get_keycloak_config():
    """Return Keycloak configuration for the frontend to initialize its client."""
    if not KEYCLOAK_URL:
        raise HTTPException(
            status_code=500,
            detail="Keycloak URL not configured by OpenTofu.",
        )
    return {
        "url": KEYCLOAK_URL,
        "realm": KEYCLOAK_REALM,
        "client_id": KEYCLOAK_CLIENT_ID,
    }
