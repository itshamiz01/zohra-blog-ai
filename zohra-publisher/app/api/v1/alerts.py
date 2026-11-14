"""
Zohra — Operational Alerts API (Part 10).

Provides:
- Alert listing with site and severity filtering
- Alert creation with deduplication and notification routing
- Alert acknowledgment and resolution lifecycle
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_role
from app.db.models.operations import UserRole
from app.db.session import get_db
from app.schemas.api import ApiResponse
from app.schemas.operations import AlertCreateRequest, AlertResponse
from app.services.alerts import AlertManager

router = APIRouter(prefix="/alerts", tags=["Alerts & Notifications"])


@router.get("", response_model=ApiResponse[list[AlertResponse]])
async def list_alerts(
    _user: Annotated[Any, Depends(require_role(UserRole.VIEWER))],
    db: Annotated[AsyncSession, Depends(get_db)],
    site_id: uuid.UUID | None = None,
    severity: str | None = None,
    limit: int = Query(50, ge=1, le=200),
) -> ApiResponse[list[AlertResponse]]:
    """List unresolved operational alerts."""
    mgr = AlertManager(db)
    alerts = await mgr.get_active_alerts(site_id=site_id, severity=severity, limit=limit)
    items = [AlertResponse.model_validate(a) for a in alerts]
    return ApiResponse(success=True, data=items)


@router.post("", response_model=ApiResponse[AlertResponse])
async def emit_alert(
    payload: AlertCreateRequest,
    user: Annotated[Any, Depends(require_role(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[AlertResponse]:
    """Emit an operational alert (manually or via integrated monitors)."""
    mgr = AlertManager(db)
    alert = await mgr.emit_alert(
        title=payload.title,
        message=payload.message,
        category=payload.category,
        severity=payload.severity,
        source=payload.source,
        site_id=payload.site_id,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        metadata=payload.metadata,
    )
    return ApiResponse(success=True, data=AlertResponse.model_validate(alert))


@router.post("/{alert_id}/acknowledge", response_model=ApiResponse[AlertResponse])
async def acknowledge_alert(
    alert_id: uuid.UUID,
    user: Annotated[Any, Depends(require_role(UserRole.EDITOR))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[AlertResponse]:
    """Acknowledge an active alert."""
    mgr = AlertManager(db)
    alert = await mgr.acknowledge_alert(alert_id, user.username)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return ApiResponse(success=True, data=AlertResponse.model_validate(alert))


@router.post("/{alert_id}/resolve", response_model=ApiResponse[AlertResponse])
async def resolve_alert(
    alert_id: uuid.UUID,
    user: Annotated[Any, Depends(require_role(UserRole.EDITOR))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[AlertResponse]:
    """Mark an alert as resolved."""
    mgr = AlertManager(db)
    alert = await mgr.resolve_alert(alert_id, user.username)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return ApiResponse(success=True, data=AlertResponse.model_validate(alert))
