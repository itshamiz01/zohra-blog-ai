"""
Zohra — Celery application configuration.

Configures the Celery worker with Redis as broker/backend,
task autodiscovery, retry policies, and structured logging.
"""

from __future__ import annotations

import os

from celery import Celery
from dotenv import load_dotenv

# Load .env for worker processes (they don't go through FastAPI startup)
load_dotenv()

celery_app = Celery(
    "zohra",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
)

celery_app.conf.update(
    # Task routing
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Task discovery
    imports=[
        "app.workers.tasks",
        "app.workers.discovery_tasks",
        "app.workers.opportunity_tasks",
        "app.workers.research_tasks",
        "app.workers.editorial_tasks",
        "app.workers.audit_tasks",
        "app.workers.publication_tasks",
        "app.workers.analytics_tasks",
        "app.workers.reddit_tasks",
        "app.workers.media_tasks",
    ],
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    worker_hijack_root_logger=False,
    # Result expiry
    result_expires=86400,  # 24 hours
    # Task execution limits
    task_soft_time_limit=300,  # 5 minutes
    task_time_limit=600,  # 10 minutes hard limit
    # Retry policy defaults
    task_default_retry_delay=10,
    task_max_retries=3,
    # Queue routing
    task_routes={
        "discovery.poll_*": {"queue": "discovery"},
        "discovery.run_query": {"queue": "discovery"},
        "discovery.process_document": {"queue": "processing"},
        "discovery.extract_entities": {"queue": "processing"},
        "discovery.find_event_cluster": {"queue": "processing"},
        "discovery.calculate_trend": {"queue": "maintenance"},
        "discovery.cleanup_old_data": {"queue": "maintenance"},
        "opportunity.process_event": {"queue": "opportunity"},
        "opportunity.reevaluate_watchlist": {"queue": "maintenance"},
        "serp.*": {"queue": "maintenance"},
        "research.*": {"queue": "research"},
        "editorial.*": {"queue": "editorial"},
        "audit.*": {"queue": "audit"},
        "publication.*": {"queue": "publication"},
        "media.*": {"queue": "publication"},
        "analytics.*": {"queue": "analytics"},
        "reddit.*": {"queue": "discovery"},
        "system.*": {"queue": "default"},
    },


    # Beat schedule for automated discovery cycles
    beat_schedule={
        "poll_all_due_sources_every_10m": {
            "task": "discovery.poll_all_due_sources",
            "schedule": 600.0,
        },
        "calculate_trend_every_15m": {
            "task": "discovery.calculate_trend",
            "schedule": 900.0,
        },
        "cleanup_old_data_daily": {
            "task": "discovery.cleanup_old_data",
            "schedule": 86400.0,
        },
        "reevaluate_opportunity_watchlist_hourly": {
            "task": "opportunity.reevaluate_watchlist",
            "schedule": 3600.0,
        },
        "cleanup_expired_serp_snapshots_daily": {
            "task": "serp.cleanup_expired_snapshots",
            "schedule": 86400.0,
        },
        "analytics_daily_sync_every_6h": {
            "task": "analytics.daily_analytics_pipeline",
            "schedule": 21600.0,  # 6 hours
            "kwargs": {"site_id": "__ALL__"},
        },
        "analytics_ctr_benchmarks_daily": {
            "task": "analytics.recalculate_ctr_benchmarks",
            "schedule": 86400.0,
            "kwargs": {"site_id": "__ALL__"},
        },
    },
)
