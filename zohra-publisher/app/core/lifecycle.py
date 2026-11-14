"""
Zohra — Application lifecycle management.

Handles startup and shutdown hooks:
  - configure logging
  - verify database connectivity
  - verify Redis connectivity
  - graceful resource cleanup on shutdown
"""

from __future__ import annotations

from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.db.session import check_database_health, close_engine
from app.utils.redis import check_redis_health, close_redis

logger = get_logger(__name__, component="lifecycle")


async def startup() -> None:
    """Application startup — called once when the process starts."""
    settings = get_settings()

    # Configure logging
    setup_logging(
        log_level=settings.LOG_LEVEL,
        environment=settings.APP_ENV.value,
    )

    logger.info(
        "Starting %s v%s [%s]",
        settings.APP_NAME,
        settings.APP_VERSION,
        settings.APP_ENV.value,
    )

    # Verify database
    db_ok = await check_database_health()
    if db_ok:
        logger.info("PostgreSQL connection verified")
    else:
        logger.error("PostgreSQL connection FAILED — application may not function correctly")

    # Verify Redis
    redis_ok = await check_redis_health()
    if redis_ok:
        logger.info("Redis connection verified")
    else:
        logger.error("Redis connection FAILED — background jobs may not function")

    # Log feature state
    logger.info(
        "Autonomy: %s | Maintenance: %s | Discovery: %s | Writing: %s | AutoPublish: %s",
        settings.AUTONOMY_ENABLED,
        settings.MAINTENANCE_MODE,
        settings.ENABLE_DISCOVERY,
        settings.ENABLE_WRITING,
        settings.ENABLE_AUTO_PUBLISH,
    )

    logger.info("Startup complete")


async def shutdown() -> None:
    """Application shutdown — graceful resource cleanup."""
    logger.info("Shutting down — releasing resources")

    await close_engine()
    logger.info("Database connections closed")

    await close_redis()
    logger.info("Redis connection closed")

    logger.info("Shutdown complete")
