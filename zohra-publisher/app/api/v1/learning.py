"""
Zohra — Part 9 Learning & Institutional Strategy Memory REST API Routes.

Implements Sections 147, 148, 218 of Part 9 Master Prompt:
- Strategy memories inspection & management
- Scoring calibration evaluation
- Strategy parameters & version management
- Bounded strategy change request approvals
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_admin_token
from app.db.models.optimization import (
    MemoryStatus,
    PredictionOutcome,
    StrategyMemory,
    StrategyParameter,
)
from app.db.session import get_db
from app.learning.engine import ZohraLearningEngine
from app.learning.strategy import StrategyParameterController
from app.schemas.api import ApiResponse
from app.schemas.optimization import (
    LearningHealthResponse,
    StrategyMemoryResponse,
    StrategyParameterResponse,
    StrategyParameterUpdate,
)

router = APIRouter(prefix="/learning", tags=["learning"])


@router.get("/health", response_model=ApiResponse[LearningHealthResponse])
async def get_learning_health(
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[LearningHealthResponse]:
    """Returns learning engine health, strategy memories volume, and calibration state."""
    stmt = select(StrategyMemory)
    res = await db.execute(stmt)
    memories = res.scalars().all()

    strong = sum(1 for m in memories if m.status == MemoryStatus.STRONG.value)
    contradicted = sum(1 for m in memories if m.status == MemoryStatus.CONTRADICTED.value)

    data = LearningHealthResponse(
        status="healthy",
        total_memories=len(memories),
        strong_memories=strong,
        contradicted_memories=contradicted,
        calibration_status="CALIBRATED",
        active_strategy_version="v1.0",
    )
    return ApiResponse(data=data)


@router.get("/memories", response_model=ApiResponse[list[StrategyMemoryResponse]])
async def list_memories(
    site_id: uuid.UUID | None = Query(default=None),
    status_filter: str | None = Query(default=None),
    _token: Annotated[dict, Depends(require_admin_token)] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[StrategyMemoryResponse]]:
    """Lists institutional strategy memories."""
    stmt = select(StrategyMemory)
    if site_id:
        stmt = stmt.where((StrategyMemory.site_id == site_id) | (StrategyMemory.scope == "GLOBAL"))
    if status_filter:
        stmt = stmt.where(StrategyMemory.status == status_filter.upper())

    stmt = stmt.order_by(StrategyMemory.confidence.desc())
    res = await db.execute(stmt)
    mems = res.scalars().all()
    return ApiResponse(data=[StrategyMemoryResponse.model_validate(m) for m in mems])


@router.post("/memories", response_model=ApiResponse[StrategyMemoryResponse], status_code=status.HTTP_201_CREATED)
async def create_memory(
    site_id: uuid.UUID | None = None,
    subject: str = Query(...),
    memory_type: str = Query(...),
    observation: str = Query(...),
    sample_size: int = Query(default=3),
    _token: Annotated[dict, Depends(require_admin_token)] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[StrategyMemoryResponse]:
    """Records an institutional strategy memory."""
    synth_res = ZohraLearningEngine.synthesize_strategy_memory(
        subject=subject,
        memory_type=memory_type,
        observation=observation,
        consistent_experiment_count=sample_size,
        site_id=site_id,
    )
    if not synth_res.memory:
        raise HTTPException(status_code=400, detail=synth_res.reason)

    db.add(synth_res.memory)
    await db.commit()
    await db.refresh(synth_res.memory)
    return ApiResponse(data=StrategyMemoryResponse.model_validate(synth_res.memory))


@router.get("/strategy", response_model=ApiResponse[list[StrategyParameterResponse]])
async def list_strategy_parameters(
    site_id: uuid.UUID | None = Query(default=None),
    _token: Annotated[dict, Depends(require_admin_token)] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[StrategyParameterResponse]]:
    """Lists bounded strategy configuration parameters."""
    stmt = select(StrategyParameter)
    if site_id:
        stmt = stmt.where((StrategyParameter.site_id == site_id) | (StrategyParameter.site_id.is_(None)))
    res = await db.execute(stmt)
    params = res.scalars().all()
    return ApiResponse(data=[StrategyParameterResponse.model_validate(p) for p in params])


@router.get("/calibration", response_model=ApiResponse[dict])
async def get_calibration_report(
    site_id: uuid.UUID = Query(...),
    _token: Annotated[dict, Depends(require_admin_token)] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    """Evaluates whether prediction scores correlate with actual 28-day performance."""
    stmt = select(PredictionOutcome).where(PredictionOutcome.site_id == site_id)
    res = await db.execute(stmt)
    outcomes = res.scalars().all()

    report = ZohraLearningEngine.evaluate_predictions_calibration(outcomes)
    return ApiResponse(data={
        "total_evaluated": report.total_evaluated,
        "is_calibrated": report.is_calibrated,
        "recalibration_needed": report.recalibration_needed,
        "mean_absolute_error": report.mean_absolute_error,
        "reasons": report.reasons,
    })


@router.post("/strategy-change-requests/{param_id}/approve", response_model=ApiResponse[dict])
async def approve_strategy_change(
    param_id: uuid.UUID,
    payload: StrategyParameterUpdate,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    """Applies a bounded adjustment to a strategy parameter."""
    stmt = select(StrategyParameter).where(StrategyParameter.id == param_id)
    res = await db.execute(stmt)
    param = res.scalar_one_or_none()
    if not param:
        raise HTTPException(status_code=404, detail="Strategy parameter not found")

    adj_res = StrategyParameterController.apply_bounded_adjustment(
        param=param,
        proposed_value=payload.proposed_value,
        evidence_ref=payload.reason,
        confidence=payload.confidence,
    )
    await db.commit()

    return ApiResponse(data={
        "parameter_name": adj_res.parameter_name,
        "previous_value": adj_res.previous_value,
        "applied_value": adj_res.applied_value,
        "clamped": adj_res.clamped,
        "rate_limited": adj_res.rate_limited,
        "reason": adj_res.reason,
    })
