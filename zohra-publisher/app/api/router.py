"""
Zohra — Central API router.

Mounts health endpoints outside versioning (infrastructure concern)
and all business endpoints under /api/v1/.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.alerts import router as alerts_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.audits import router as audits_router
from app.api.v1.backups import router as backups_router
from app.api.v1.discovery import router as discovery_router
from app.api.v1.drafts import router as drafts_router
from app.api.v1.events import router as events_router
from app.api.v1.experiments import router as experiments_router
from app.api.v1.health import router as health_router
from app.api.v1.keywords import router as keywords_router
from app.api.v1.learning import router as learning_router
from app.api.v1.media import router as media_router

# Part 10 routers
from app.api.v1.operations import router as operations_router
from app.api.v1.opportunities import router as opportunities_router
from app.api.v1.optimization import router as optimization_router
from app.api.v1.publications import router as publications_router
from app.api.v1.reddit import router as reddit_router
from app.api.v1.research import router as research_router
from app.api.v1.secrets import router as secrets_router
from app.api.v1.sites import router as sites_router
from app.api.v1.sources import router as sources_router
from app.api.v1.system import router as system_router
from app.api.v1.topic_clusters import router as topic_clusters_router
from app.api.v1.trends import router as trends_router
from app.api.v1.users import router as users_router

# Health endpoints — outside API versioning (infrastructure)
health_routes = health_router

# Versioned business API
api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(system_router)
api_v1_router.include_router(admin_router)
api_v1_router.include_router(sources_router)
api_v1_router.include_router(events_router)
api_v1_router.include_router(trends_router)
api_v1_router.include_router(discovery_router)
api_v1_router.include_router(sites_router)
api_v1_router.include_router(opportunities_router)
api_v1_router.include_router(keywords_router)
api_v1_router.include_router(topic_clusters_router)
api_v1_router.include_router(research_router)
api_v1_router.include_router(drafts_router)
api_v1_router.include_router(audits_router)
api_v1_router.include_router(publications_router)
api_v1_router.include_router(analytics_router)
api_v1_router.include_router(optimization_router)
api_v1_router.include_router(experiments_router)
api_v1_router.include_router(learning_router)
api_v1_router.include_router(reddit_router)
api_v1_router.include_router(media_router)

# Part 10 endpoints
api_v1_router.include_router(operations_router)
api_v1_router.include_router(alerts_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(backups_router)
api_v1_router.include_router(secrets_router)


