"""Zohra — Audit Logging Service.

Records tamper-evident, immutable audit trail entries across the engine.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit_logs import AuditLog


class AuditService:
    @staticmethod
    async def log_action(
        db: AsyncSession,
        action: str,
        entity_type: str | None = None,
        entity_id: str | uuid.UUID | None = None,
        actor_id: str | None = None,
        actor_type: str = "admin",
        changes: dict[str, Any] | None = None,
        previous_state: str | None = None,
        new_state: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        metadata_json: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Create an audit log record within the current transaction."""
        parsed_entity_id = None
        if entity_id:
            if isinstance(entity_id, uuid.UUID):
                parsed_entity_id = entity_id
            else:
                try:
                    parsed_entity_id = uuid.UUID(str(entity_id))
                except (ValueError, TypeError):
                    parsed_entity_id = None

        meta = dict(metadata_json or {})
        if changes:
            meta["changes"] = changes
        if user_agent:
            meta["user_agent"] = user_agent

        log_entry = AuditLog(
            action=action,
            actor_type=actor_type,
            actor_id=str(actor_id) if actor_id is not None else None,
            entity_type=entity_type,
            entity_id=parsed_entity_id,
            previous_state=previous_state,
            new_state=new_state,
            ip_address=ip_address,
            metadata_json=meta,
        )
        db.add(log_entry)
        await db.flush()
        return log_entry
