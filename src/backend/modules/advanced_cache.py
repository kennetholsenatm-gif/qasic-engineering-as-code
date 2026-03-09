"""
Optional advanced cache (e.g. ElastiCache) integration.
Exposes a status endpoint when FEATURE_ELASTICACHE_ENABLED is set.
"""
from fastapi import APIRouter

cache_router = APIRouter()


@cache_router.get("/status")
def get_cache_status():
    """Return cache status for the frontend. Stub when no real cache client is configured."""
    return {"status": "enabled", "backend": "elasticache_stub"}
