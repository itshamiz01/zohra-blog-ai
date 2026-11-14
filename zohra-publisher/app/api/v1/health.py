"""
Zohra — Health check endpoints.

GET /health        — overall health status
GET /health/live   — process is alive
GET /health/ready  — dependencies are functioning
"""

from __future__ import annotations

import time

from fastapi import APIRouter

from app.core.config import get_settings
from app.db.session import check_database_health
from app.schemas.api import HealthResponse, ServiceHealth
from app.utils.redis import check_redis_health

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Overall health — checks all dependencies."""
    settings = get_settings()

    # Database check
    db_start = time.monotonic()
    db_ok = await check_database_health()
    db_ms = (time.monotonic() - db_start) * 1000

    # Redis check
    redis_start = time.monotonic()
    redis_ok = await check_redis_health()
    redis_ms = (time.monotonic() - redis_start) * 1000

    all_healthy = db_ok and redis_ok

    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        version=settings.APP_VERSION,
        environment=settings.APP_ENV.value,
        services={
            "database": ServiceHealth(
                status="healthy" if db_ok else "unhealthy",
                latency_ms=round(db_ms, 2),
            ),
            "redis": ServiceHealth(
                status="healthy" if redis_ok else "unhealthy",
                latency_ms=round(redis_ms, 2),
            ),
        },
    )


@router.get("/health/live")
async def liveness() -> dict:
    """Liveness probe — the process is alive and responding."""
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness() -> dict:
    """Readiness probe — all required dependencies are available."""
    db_ok = await check_database_health()
    redis_ok = await check_redis_health()

    if not db_ok or not redis_ok:
        # Return 503 so load balancers can route traffic elsewhere
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "database": "healthy" if db_ok else "unhealthy",
                "redis": "healthy" if redis_ok else "unhealthy",
            },
        )

    return {
        "status": "ready",
        "database": "healthy",
        "redis": "healthy",
    }
