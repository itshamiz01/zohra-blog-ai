"""
Zohra — Event Handoff Contract for Part 3.

Provides the structured contract that transfers qualified discovered events
to Part 3 (Content Strategy, SEO Opportunity & Brief Engine).
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.entities import DocumentEntity, Entity
from app.db.models.event_documents import EventDocument
from app.db.models.events import Event
from app.db.models.source_documents import SourceDocument
from app.db.models.sources import Source


@dataclass
class QualifiedEventHandoff:
    """The clean contract delivered from Part 2 to Part 3."""

    event_id: str
    canonical_title: str
    summary: str | None
    category: str
    event_type: str
    language: str
    countries: list[str] = field(default_factory=list)
    first_seen_at: str = ""
    last_seen_at: str = ""
    trend_score: float = 0.0
    velocity_score: float = 0.0
    momentum_score: float = 0.0
    confidence_score: float = 0.0
    source_diversity_score: float = 0.0
    entities: list[dict[str, Any]] = field(default_factory=list)
    primary_sources: list[dict[str, Any]] = field(default_factory=list)
    supporting_sources: list[dict[str, Any]] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    high_verification_required: bool = False
    contradiction_detected: bool = False
    trend_reasons: list[str] = field(default_factory=list)
    status: str = "emerging"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


async def build_event_handoff(
    session: AsyncSession, event_id: uuid.UUID
) -> QualifiedEventHandoff | None:
    """
    Builds the complete Part 3 handoff contract object for an event from the database.
    """
    res_ev = await session.execute(select(Event).where(Event.id == event_id))
    event = res_ev.scalar_one_or_none()
    if not event:
        return None

    # Fetch attached documents and their sources
    stmt_docs = (
        select(EventDocument, SourceDocument, Source)
        .join(SourceDocument, EventDocument.document_id == SourceDocument.id)
        .join(Source, SourceDocument.source_id == Source.id)
        .where(EventDocument.event_id == event_id)
    )
    res_docs = await session.execute(stmt_docs)
    doc_rows = res_docs.all()

    primary_sources: list[dict[str, Any]] = []
    supporting_sources: list[dict[str, Any]] = []
    countries_set: set[str] = set()

    for ed, doc, src in doc_rows:
        if doc.country:
            countries_set.add(doc.country)

        src_info = {
            "document_id": str(doc.id),
            "source_id": str(src.id),
            "source_name": src.name,
            "domain": src.domain,
            "tier": src.tier,
            "authority_score": src.authority_score,
            "url": doc.url,
            "canonical_url": doc.canonical_url,
            "title": doc.title,
            "published_at": doc.published_at.isoformat() if doc.published_at else None,
            "similarity_score": ed.similarity_score,
        }

        if ed.is_primary_source or src.tier == 1:
            primary_sources.append(src_info)
        else:
            supporting_sources.append(src_info)

    # Fetch attached entities
    doc_ids = [doc.id for _, doc, _ in doc_rows]
    entities_list: list[dict[str, Any]] = []

    if doc_ids:
        stmt_ent = (
            select(
                Entity.canonical_name,
                Entity.entity_type,
                DocumentEntity.confidence,
                DocumentEntity.mentions,
            )
            .join(DocumentEntity, Entity.id == DocumentEntity.entity_id)
            .where(DocumentEntity.document_id.in_(doc_ids))
        )
        res_ent = await session.execute(stmt_ent)
        for canon, etype, conf, mentions in res_ent.all():
            entities_list.append(
                {
                    "name": canon,
                    "type": etype,
                    "confidence": conf,
                    "mentions": mentions,
                }
            )

    return QualifiedEventHandoff(
        event_id=str(event.id),
        canonical_title=event.canonical_title,
        summary=event.summary,
        category=event.primary_category,
        event_type=event.event_type,
        language=event.language or "en",
        countries=sorted(countries_set),
        first_seen_at=event.first_seen_at.isoformat(),
        last_seen_at=event.last_seen_at.isoformat(),
        trend_score=event.trend_score,
        velocity_score=event.velocity_score,
        momentum_score=event.momentum_score,
        confidence_score=event.confidence_score,
        source_diversity_score=event.source_diversity_score,
        entities=entities_list,
        primary_sources=primary_sources,
        supporting_sources=supporting_sources,
        risk_flags=event.risk_flags or [],
        high_verification_required=event.high_verification_required,
        contradiction_detected=event.contradiction_detected,
        trend_reasons=event.trend_reasons or [],
        status=event.status,
    )
