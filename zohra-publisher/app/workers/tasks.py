"""
Zohra — Celery tasks.

Part 1 provides a health-check task to verify the
FastAPI → Redis → Celery → Result pipeline works end-to-end.

Future parts will add discovery, research, writing, and publishing tasks.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.workers.celery_app import celery_app


@celery_app.task(name="system.health_check", bind=True)
def system_health_check(self) -> dict:
    """
    Smoke test: proves that a Celery worker can receive and
    process a task dispatched from FastAPI via Redis.
    """
    return {
        "status": "healthy",
        "worker": self.request.hostname,
        "task_id": self.request.id,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@celery_app.task(name="system.echo", bind=True, max_retries=2)
def system_echo(self, message: str) -> dict:
    """Echo task for integration testing."""
    return {
        "echo": message,
        "worker": self.request.hostname,
        "task_id": self.request.id,
        "timestamp": datetime.now(UTC).isoformat(),
    }
