"""
Zohra — Discovery Pipeline Coordinator.

Orchestrates the entire discovery and ingestion cycle:
1. Fetch items via appropriate adapter with SSRF & size protections
2. Normalize canonical URLs and check Level 1-4 deduplication
3. Sanitize HTML and clean text into inert data
4. Extract entities, normalize canonical names, and detect language/country
5. Classify categories, detect risk flags, and compute spam probability
6. Store SourceDocument and DocumentEntity associations
7. Cluster into existing Event or create a new Event cluster
8. Recalculate event metrics: velocity, momentum, diversity, freshness, confidence, trend
9. Evaluate event lifecycle state and Part 3 qualification
10. Record EventSnapshot for historical tracking.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models.entities import DocumentEntity, Entity
from app.db.models.event_documents import EventDocument
from app.db.models.event_snapshots import EventSnapshot
from app.db.models.events import Event
from app.db.models.source_documents import SourceDocument
from app.db.models.sources import Source
from app.discovery.adapters.base import RawFetchedItem
from app.discovery.adapters.rss import RSSAdapter
from app.discovery.clustering.engine import EventClusteringEngine
from app.discovery.dedup.detector import compute_simhash, is_near_duplicate
from app.discovery.nlp.entities import extract_entities
from app.discovery.nlp.geography import detect_country
from app.discovery.nlp.language import detect_language
from app.discovery.nlp.risk import detect_risk_flags
from app.discovery.nlp.topics import classify_topics
from app.discovery.normalizer.content import (
    compute_content_hash,
    compute_title_hash,
    compute_word_count,
    extract_clean_summary,
)
from app.discovery.normalizer.url import normalize_canonical_url
from app.discovery.scoring.confidence import calculate_event_confidence_score, detect_contradictions
from app.discovery.scoring.diversity import calculate_source_diversity_score
from app.discovery.scoring.freshness import calculate_freshness_score
from app.discovery.scoring.lifecycle import evaluate_lifecycle_state
from app.discovery.scoring.momentum import calculate_momentum_score
from app.discovery.scoring.spam import evaluate_spam_probability
from app.discovery.scoring.trend import (
    calculate_trend_score,
    classify_trend,
    generate_trend_reasons,
    is_event_qualified_for_part3,
)
from app.discovery.scoring.velocity import calculate_velocity_and_acceleration
from app.discovery.security.circuit_breaker import SourceCircuitBreaker
from app.discovery.security.firewall import inspect_and_disarm
from app.discovery.security.sanitizer import sanitize_text

logger = get_logger("discovery.pipeline")


def _ensure_utc(dt: datetime | None) -> datetime:
    """Normalize datetime to timezone-aware UTC, even if SQLite returns a naive datetime."""
    if dt is None:
        return datetime.now(UTC)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


class DiscoveryPipeline:
    """End-to-end autonomous discovery processor."""

    def __init__(
        self,
        session: AsyncSession | None = None,
        db: AsyncSession | None = None,
    ) -> None:
        self.session = session or db
        if not self.session:
            raise ValueError(
                "DiscoveryPipeline requires a valid AsyncSession (passed as session= or db=)"
            )
        self.settings = get_settings()
        self.rss_adapter = RSSAdapter()
        self.clustering_engine = EventClusteringEngine()
        self.circuit_breaker = SourceCircuitBreaker()

    async def poll_source(self, source_id: uuid.UUID) -> dict[str, Any]:
        """Poll a single source via RSSAdapter and process all incoming items."""
        stmt = select(Source).where(Source.id == source_id)
        res = await self.session.execute(stmt)
        source = res.scalar_one_or_none()
        if not source:
            return {"error": f"Source {source_id} not found", "items_processed": 0}

        now = datetime.now(UTC)
        fetch_res = await self.rss_adapter.fetch(source.base_url)
        source.last_checked_at = now

        if not fetch_res.success:
            source.consecutive_failure_count = (source.consecutive_failure_count or 0) + 1
            source.health_status = "degraded" if source.consecutive_failure_count < 3 else "failing"
            return {
                "source_id": str(source.id),
                "success": False,
                "error": fetch_res.error_message,
                "items_processed": 0,
            }

        source.consecutive_failure_count = 0
        source.health_status = "healthy"
        processed_count = 0
        new_events_count = 0

        for item in fetch_res.items:
            doc, event, is_new = await self.process_raw_item(source=source, raw_item=item)
            if doc:
                processed_count += 1
            if is_new:
                new_events_count += 1

        return {
            "source_id": str(source.id),
            "source_name": source.name,
            "success": True,
            "items_fetched": len(fetch_res.items),
            "documents_processed": processed_count,
            "new_events_created": new_events_count,
        }

    async def run_cycle(self, source_ids: list[uuid.UUID] | None = None) -> dict[str, Any]:
        """Execute a full discovery run cycle over specified or all enabled sources."""
        query = select(Source).where(Source.is_enabled.is_(True))
        if source_ids:
            query = query.where(Source.id.in_(source_ids))
        res = await self.session.execute(query)
        sources = list(res.scalars().all())

        total_fetched = 0
        total_processed = 0
        new_events = 0

        for src in sources:
            res_poll = await self.poll_source(src.id)
            total_fetched += res_poll.get("items_fetched", 0)
            total_processed += res_poll.get("documents_processed", 0)
            new_events += res_poll.get("new_events_created", 0)

        await self.session.flush()

        return {
            "sources_polled": len(sources),
            "items_fetched": total_fetched,
            "documents_processed": total_processed,
            "new_events_created": new_events,
            "cycle_completed_at": datetime.now(UTC).isoformat(),
        }

    async def _ingest_raw_item(
        self,
        source: Source,
        item: RawFetchedItem,
    ) -> SourceDocument | None:
        """Convenience method returning the ingested/matched SourceDocument."""
        doc, _, _ = await self.process_raw_item(source=source, raw_item=item)
        return doc

    async def process_raw_item(
        self,
        source: Source,
        raw_item: RawFetchedItem,
    ) -> tuple[SourceDocument | None, Event | None, bool]:
        """
        Processes a single raw item through the pipeline.
        Returns (source_document, event, is_new_event).
        If item is an exact duplicate, returns existing document and its event.
        """
        now = datetime.now(UTC)

        # 1. URL Canonicalization & Hashing
        canonical_url = normalize_canonical_url(raw_item.url)
        content_clean = sanitize_text(raw_item.content_text or raw_item.summary or "")
        summary_clean = extract_clean_summary(raw_item.summary or content_clean)
        title_clean = sanitize_text(raw_item.title)

        content_hash = compute_content_hash(content_clean)
        title_hash = compute_title_hash(title_clean)
        simhash_val = compute_simhash(content_clean or title_clean)
        word_count = compute_word_count(content_clean)

        # 2. Level 1 & 2 Deduplication: Check if canonical URL or external_id exists
        stmt_dup = select(SourceDocument).where(
            (SourceDocument.canonical_url == canonical_url)
            | (
                (SourceDocument.source_id == source.id)
                & (SourceDocument.external_id == raw_item.external_id)
                & (SourceDocument.external_id.is_not(None))
            )
        )
        res_dup = await self.session.execute(stmt_dup)
        existing_doc = res_dup.scalar_one_or_none()
        if existing_doc:
            logger.debug("Exact duplicate document identified", url=canonical_url)
            # Create a duplicate record referencing the original document
            dup_doc = SourceDocument(
                source_id=source.id,
                external_id=raw_item.external_id,
                url=raw_item.url,
                canonical_url=canonical_url,
                title=title_clean,
                summary=summary_clean,
                content_text=content_clean,
                author=raw_item.author,
                published_at=raw_item.published_at or now,
                discovered_at=now,
                fetched_at=now,
                language=existing_doc.language,
                language_confidence=existing_doc.language_confidence,
                country=existing_doc.country,
                content_hash=content_hash,
                title_hash=title_hash,
                simhash=simhash_val,
                source_type=source.source_type,
                word_count=word_count,
                spam_probability=existing_doc.spam_probability,
                is_duplicate=True,
                is_exact_duplicate=True,
                is_near_duplicate=False,
                duplicate_of_id=existing_doc.id,
                metadata_json={"duplicate_type": "url_or_external_id"},
            )
            self.session.add(dup_doc)
            await self.session.flush()

            # Find associated event
            res_ed = await self.session.execute(
                select(Event)
                .join(EventDocument, Event.id == EventDocument.event_id)
                .where(EventDocument.document_id == existing_doc.id)
            )
            ev = res_ed.scalar_one_or_none()
            return dup_doc, ev, False

        # 3. Level 3 Deduplication: Exact content hash match
        res_hash = await self.session.execute(
            select(SourceDocument).where(SourceDocument.content_hash == content_hash)
        )
        hash_dup = res_hash.scalar_one_or_none()
        is_exact_content_dup = hash_dup is not None

        # 4. Level 4 Deduplication: Near-duplicate check against recent documents
        is_near_dup = False
        near_dup_doc_id = None
        if not is_exact_content_dup:
            res_recent = await self.session.execute(
                select(SourceDocument.id, SourceDocument.simhash, SourceDocument.title)
                .where(SourceDocument.is_duplicate.is_(False))
                .order_by(SourceDocument.discovered_at.desc())
                .limit(100)
            )
            for r_id, r_simhash, r_title in res_recent.all():
                if r_simhash:
                    dup, _ = is_near_duplicate(simhash_val, r_simhash, title_clean, r_title)
                    if dup:
                        is_near_dup = True
                        near_dup_doc_id = r_id
                        break

        # 5. Language & Country detection
        lang_code, lang_conf = detect_language(f"{title_clean} {content_clean}")
        country_code = detect_country(
            content_clean, url=canonical_url, source_country=source.country
        )

        # 6. Entity & Topic Extraction
        extracted_entities = extract_entities(f"{title_clean}. {content_clean}")
        has_person = any(e.entity_type.value == "PERSON" for e in extracted_entities)
        primary_cat, cat_scores = classify_topics(f"{title_clean} {content_clean}")

        # 7. Risk Flags & Spam
        risk_flags, high_verification = detect_risk_flags(
            f"{title_clean} {content_clean}", has_person_entity=has_person
        )
        spam_prob = evaluate_spam_probability(
            title=title_clean,
            content=content_clean,
            source_tier=source.tier,
            source_reliability=source.reliability_score,
        )

        # 8. Prompt-Injection Firewall inspection
        firewall_result = inspect_and_disarm(content_clean)

        # 9. Create SourceDocument
        published = raw_item.published_at or now
        if published.tzinfo is None:
            published = published.replace(tzinfo=UTC)

        doc = SourceDocument(
            source_id=source.id,
            external_id=raw_item.external_id,
            url=raw_item.url,
            canonical_url=canonical_url,
            title=title_clean,
            summary=summary_clean,
            content_text=firewall_result.sanitized_content,
            author=raw_item.author,
            published_at=published,
            discovered_at=now,
            fetched_at=now,
            language=lang_code,
            language_confidence=lang_conf,
            country=country_code,
            content_hash=content_hash,
            title_hash=title_hash,
            simhash=simhash_val,
            source_type=source.source_type,
            word_count=word_count,
            spam_probability=spam_prob,
            is_duplicate=(is_exact_content_dup or is_near_dup),
            is_exact_duplicate=is_exact_content_dup,
            is_near_duplicate=is_near_dup,
            duplicate_of_id=(hash_dup.id if hash_dup else near_dup_doc_id),
            metadata_json={
                "firewall_injection_detected": firewall_result.injection_detected,
                "categories": cat_scores,
                "risk_flags": risk_flags,
            },
        )
        self.session.add(doc)
        await self.session.flush()

        # 10. Persist DocumentEntity links
        for ee in extracted_entities:
            # Upsert Entity
            res_e = await self.session.execute(
                select(Entity).where(Entity.normalized_name == ee.normalized_name)
            )
            entity_record = res_e.scalar_one_or_none()
            if not entity_record:
                entity_record = Entity(
                    entity_type=ee.entity_type.value,
                    canonical_name=ee.canonical_name,
                    normalized_name=ee.normalized_name,
                    aliases=ee.aliases,
                    mention_count=1,
                )
                self.session.add(entity_record)
                await self.session.flush()
            else:
                entity_record.mention_count += 1

            doc_entity = DocumentEntity(
                document_id=doc.id,
                entity_id=entity_record.id,
                confidence=ee.confidence,
                mentions=ee.mentions,
            )
            self.session.add(doc_entity)

        # 11. Event Clustering: Query candidate events in time window
        window_start = (
            now
            - (published - now if published < now else now - published)
            - (published - published)
        )  # Clean timedelta
        from datetime import timedelta

        window_start = now - timedelta(hours=self.settings.EVENT_CLUSTER_WINDOW_HOURS)

        res_events = await self.session.execute(
            select(Event).where(
                Event.status.notin_(["archived", "rejected"]),
                Event.last_seen_at >= window_start,
            )
        )
        existing_events = res_events.scalars().all()

        candidate_dicts = []
        for ev in existing_events:
            ev_entities = extract_entities(f"{ev.canonical_title}. {ev.summary or ''}")
            candidate_dicts.append(
                {
                    "id": ev.id,
                    "canonical_title": ev.canonical_title,
                    "summary": ev.summary,
                    "primary_category": ev.primary_category,
                    "first_seen_at": _ensure_utc(ev.first_seen_at),
                    "last_seen_at": _ensure_utc(ev.last_seen_at),
                    "entity_keys": [e.normalized_name for e in ev_entities],
                }
            )

        cluster_match = await self.clustering_engine.find_best_cluster(
            doc_title=title_clean,
            doc_summary=summary_clean,
            doc_category=primary_cat,
            doc_entities=extracted_entities,
            doc_time=published,
            candidate_events=candidate_dicts,
        )

        target_event: Event
        is_new_event = False

        if (
            cluster_match
            and cluster_match.similarity_score >= self.settings.EVENT_SIMILARITY_THRESHOLD
        ):
            # Attach to matched existing event
            res_target = await self.session.execute(
                select(Event).where(Event.id == uuid.UUID(cluster_match.event_id))
            )
            target_event = res_target.scalar_one()
            target_event.last_seen_at = max(_ensure_utc(target_event.last_seen_at), published)
            target_event.document_count += 1

            # Check if this source is new to the event
            res_src_count = await self.session.execute(
                select(SourceDocument.source_id)
                .join(EventDocument, SourceDocument.id == EventDocument.document_id)
                .where(EventDocument.event_id == target_event.id)
            )
            existing_sources = set(res_src_count.scalars().all())
            if source.id not in existing_sources:
                target_event.source_count += 1

            # Attach EventDocument
            event_doc = EventDocument(
                event_id=target_event.id,
                document_id=doc.id,
                similarity_score=cluster_match.similarity_score,
                relevance_score=cluster_match.title_similarity,
                is_primary_source=(source.tier == 1),
            )
            self.session.add(event_doc)

        else:
            # Create a brand new Event cluster
            is_new_event = True
            target_event = Event(
                canonical_title=title_clean,
                summary=summary_clean,
                primary_category=primary_cat,
                categories=cat_scores,
                event_type="announcement",
                first_seen_at=published,
                last_seen_at=published,
                status="emerging",
                source_count=1,
                document_count=1,
                authority_score=source.authority_score,
                reliability_score=source.reliability_score,
                freshness_score=100.0,
                language=lang_code,
                country=country_code,
                primary_source_document_id=doc.id,
                risk_flags=risk_flags,
                high_verification_required=high_verification,
            )
            self.session.add(target_event)
            await self.session.flush()

            # Attach initial EventDocument
            event_doc = EventDocument(
                event_id=target_event.id,
                document_id=doc.id,
                similarity_score=1.0,
                relevance_score=1.0,
                is_primary_source=(source.tier == 1),
            )
            self.session.add(event_doc)

        # 12. Recalculate event metrics & signals
        await self.recalculate_event_signals(target_event, now)

        await self.session.flush()
        return doc, target_event, is_new_event

    async def recalculate_event_signals(self, event: Event, now: datetime | None = None) -> None:
        """
        Recalculates velocity, momentum, diversity, freshness, confidence,
        trend score, lifecycle state, and qualification for an event.
        """
        current_time = _ensure_utc(now)

        # Query all documents in event
        stmt = (
            select(SourceDocument, Source)
            .join(EventDocument, SourceDocument.id == EventDocument.document_id)
            .join(Source, SourceDocument.source_id == Source.id)
            .where(EventDocument.event_id == event.id)
        )
        rows = (await self.session.execute(stmt)).all()
        if not rows:
            return

        docs = [r[0] for r in rows]
        sources = [r[1] for r in rows]

        doc_timestamps = [_ensure_utc(d.published_at or d.discovered_at) for d in docs]
        domains = [s.domain for s in sources]
        tiers = [s.tier for s in sources]
        countries = [d.country or s.country or "" for d, s in zip(docs, sources, strict=False)]
        reliabilities = [s.reliability_score for s in sources]
        authorities = [s.authority_score for s in sources]

        # 1. Velocity & Acceleration
        velocity_score, accel_ratio, counts = calculate_velocity_and_acceleration(
            doc_timestamps, current_time
        )
        event.velocity_score = velocity_score

        # 2. Freshness
        freshness = calculate_freshness_score(
            _ensure_utc(event.first_seen_at),
            _ensure_utc(event.last_seen_at),
            event.primary_category,
            current_time,
        )
        event.freshness_score = freshness

        # 3. Momentum
        momentum = calculate_momentum_score(
            velocity_score, accel_ratio, event.source_count, freshness
        )
        event.momentum_score = momentum

        # 4. Source Diversity
        diversity = calculate_source_diversity_score(domains, tiers, countries)
        event.source_diversity_score = diversity

        # 5. Contradictions & Confidence
        titles_and_texts = [f"{d.title}. {d.summary or ''}" for d in docs]
        has_contra, contra_list = detect_contradictions(titles_and_texts)
        event.contradiction_detected = has_contra
        event.contradictions_json = contra_list if has_contra else None

        avg_authority = sum(authorities) / len(authorities) if authorities else 50.0
        event.authority_score = round(avg_authority, 2)

        conf_score = calculate_event_confidence_score(
            reliabilities, tiers, len(set(domains)), has_contra
        )
        event.confidence_score = conf_score

        # 6. Trend Score & Classification
        trend_score = calculate_trend_score(
            velocity_score=velocity_score,
            momentum_score=momentum,
            diversity_score=diversity,
            freshness_score=freshness,
            authority_score=avg_authority,
            confidence_score=conf_score,
        )
        event.trend_score = trend_score
        event.trend_classification = classify_trend(trend_score).value

        # 7. Explainability
        event.trend_reasons = generate_trend_reasons(
            velocity_score=velocity_score,
            momentum_score=momentum,
            diversity_score=diversity,
            freshness_score=freshness,
            authority_score=avg_authority,
            confidence_score=conf_score,
            source_count=event.source_count,
            document_count=event.document_count,
            has_tier1=(1 in tiers),
            acceleration_ratio=accel_ratio,
            contradiction_detected=has_contra,
        )

        # 8. Lifecycle State
        avg_spam = sum(d.spam_probability for d in docs) / len(docs)
        new_status = evaluate_lifecycle_state(
            current_status=event.status,
            document_count=event.document_count,
            source_count=event.source_count,
            velocity_score=velocity_score,
            acceleration_ratio=accel_ratio,
            freshness_score=freshness,
            spam_probability=avg_spam,
        )
        event.status = new_status.value

        # 9. Qualification for Part 3
        is_qual, rej_reason = is_event_qualified_for_part3(
            trend_score=trend_score,
            confidence_score=conf_score,
            spam_probability=avg_spam,
            status=event.status,
            min_trend=self.settings.MIN_TREND_SCORE_FOR_HANDOFF,
            min_confidence=self.settings.MIN_CONFIDENCE_FOR_HANDOFF,
        )
        event.is_qualified_for_part3 = is_qual
        event.rejection_reason = rej_reason

        # 10. Record Snapshot
        snapshot = EventSnapshot(
            event_id=event.id,
            snapshot_time=current_time,
            document_count=event.document_count,
            source_count=event.source_count,
            velocity_score=velocity_score,
            momentum_score=momentum,
            trend_score=trend_score,
            confidence_score=conf_score,
            status=event.status,
            metadata_json={"trend_classification": event.trend_classification},
        )
        self.session.add(snapshot)
