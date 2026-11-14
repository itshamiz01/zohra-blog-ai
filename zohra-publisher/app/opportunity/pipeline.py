"""
Zohra — Content Opportunity Intelligence Pipeline Orchestrator.

Processes Part 2 qualified events through the complete opportunity intelligence cycle:
relevance filter -> keyword expansion -> intent classification -> clustering ->
SERP retrieval -> competition & content gaps -> cannibalization check ->
angle generation -> multi-profile scoring & gating -> Part 4 package delivery.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import AnalysisDepth, ContentAction, OpportunityStatus
from app.core.logging import get_logger
from app.db.models.content_gaps import ContentGap
from app.db.models.content_opportunities import ContentOpportunity
from app.db.models.keyword_clusters import KeywordCluster, KeywordClusterMember
from app.db.models.keywords import Keyword
from app.db.models.opportunity_snapshots import OpportunitySnapshot, OpportunityWatchlist
from app.db.models.questions import DiscoveredQuestion
from app.db.models.serp import SERPResult, SERPSnapshot
from app.db.models.site_content import SiteContent
from app.db.models.site_topics import SiteTopic
from app.db.models.sites import Site
from app.discovery.handoff import QualifiedEventHandoff
from app.opportunity.angles.generator import AngleGenerator
from app.opportunity.clustering.engine import KeywordClusteringEngine
from app.opportunity.competition.analyzer import CompetitionAnalyzer
from app.opportunity.handoff import build_opportunity_package
from app.opportunity.keywords.expander import KeywordExpander
from app.opportunity.scoring.engine import OpportunityScoringEngine, ScoringInput
from app.opportunity.serp.analyzer import SERPAnalyzer
from app.opportunity.serp.provider import SERPProvider, get_serp_provider
from app.opportunity.site.cannibalization import CannibalizationDetector
from app.opportunity.site.relevance import SiteRelevanceScorer
from app.schemas.opportunity import ContentOpportunityPackage
from app.utils.redis import distributed_lock

logger = get_logger(__name__, component="opportunity_pipeline")


class OpportunityPipeline:
    """Master orchestrator for content opportunity analysis."""

    def __init__(self, serp_provider: SERPProvider | None = None) -> None:
        self.relevance_scorer = SiteRelevanceScorer(min_relevance_threshold=35.0)
        self.keyword_expander = KeywordExpander()
        self.clustering_engine = KeywordClusteringEngine()
        self.serp_provider = serp_provider or get_serp_provider()
        self.serp_analyzer = SERPAnalyzer()
        self.competition_analyzer = CompetitionAnalyzer()
        self.cannibalization_detector = CannibalizationDetector()
        self.angle_generator = AngleGenerator()
        self.scoring_engine = OpportunityScoringEngine()

    async def get_or_create_default_site(self, session: AsyncSession) -> Site:
        """Finds or seeds the default publication site."""
        stmt = select(Site).where(Site.domain == settings.DEFAULT_SITE_DOMAIN)
        result = await session.execute(stmt)
        site = result.scalar_one_or_none()

        if not site:
            site = Site(
                name="Zohra AI Publishing Network",
                domain=settings.DEFAULT_SITE_DOMAIN,
                default_language="en",
                primary_country="global",
                niche="Artificial Intelligence, Developer Tools, Software Automation & Creators",
                description="Authoritative publication covering AI engineering, models, automation tutorials, and creator tools.",
                target_audiences=["developers", "AI engineers", "creators", "tech enthusiasts", "business owners"],
                enabled=True,
            )
            session.add(site)
            await session.flush()

            # Seed core topic relevance weights
            default_topics = [
                ("Artificial Intelligence", "artificial-intelligence", 1.0, 75.0),
                ("Machine Learning", "machine-learning", 0.95, 70.0),
                ("Software Automation", "software-automation", 0.90, 68.0),
                ("Developer Tools", "developer-tools", 0.88, 65.0),
                ("Content Creation", "content-creation", 0.80, 60.0),
            ]
            for tname, slug, rel, auth in default_topics:
                stopic = SiteTopic(
                    site_id=site.id,
                    topic_name=tname,
                    canonical_slug=slug,
                    relevance_weight=rel,
                    topical_authority_score=auth,
                    historical_post_count=10,
                )
                session.add(stopic)
            await session.flush()

        return site

    async def process_event(
        self,
        session: AsyncSession,
        event_handoff: QualifiedEventHandoff,
        site_id: uuid.UUID | None = None,
        depth: AnalysisDepth = AnalysisDepth.STANDARD,
    ) -> list[ContentOpportunityPackage]:
        """
        Executes end-to-end opportunity intelligence on a qualified event.
        Returns a list of qualified ContentOpportunityPackages ready for Part 4.
        """
        event_uuid = uuid.UUID(event_handoff.event_id)

        # 1. Resolve Target Site
        if site_id:
            site = await session.get(Site, site_id)
            if not site:
                site = await self.get_or_create_default_site(session)
        else:
            site = await self.get_or_create_default_site(session)

        # Distributed Lock to prevent duplicate concurrent runs on same event + site
        lock_res = f"opportunity:event:{event_handoff.event_id}:site:{site.id}"
        async with distributed_lock(lock_res, ttl_seconds=120) as acquired:
            if not acquired:
                logger.warning(
                    "opportunity_analysis_already_locked",
                    event_id=event_handoff.event_id,
                    site_id=str(site.id),
                )
                return []

            # Load Site Topics
            topic_stmt = select(SiteTopic).where(SiteTopic.site_id == site.id)
            topic_res = await session.execute(topic_stmt)
            site_topics = list(topic_res.scalars().all())

            # 2. Stage 1: Cost-Aware Funneling — Site Relevance Pre-Filter
            rel_result = self.relevance_scorer.calculate(
                site=site,
                topics=site_topics,
                event_title=event_handoff.canonical_title,
                event_summary=event_handoff.summary,
                event_category=event_handoff.category,
                entities=event_handoff.entities,
                target_audience=site.target_audiences,
                language=event_handoff.language,
            )

            # SCENARIO A: Huge trend, completely irrelevant to site -> REJECT EARLY
            if not rel_result.is_eligible:
                logger.info(
                    "event_rejected_by_site_relevance",
                    event_id=event_handoff.event_id,
                    title=event_handoff.canonical_title,
                    relevance_score=rel_result.site_relevance_score,
                    reason=rel_result.rejection_reason,
                )
                # Persist rejected candidate opportunity record for transparency & audit
                rejected_opp = ContentOpportunity(
                    event_id=event_uuid,
                    site_id=site.id,
                    canonical_topic=event_handoff.canonical_title,
                    proposed_angle="Irrelevant to Site Profile",
                    working_title=event_handoff.canonical_title,
                    primary_keyword=event_handoff.canonical_title.lower(),
                    primary_intent="news",
                    content_type="breaking_news",
                    language=event_handoff.language,
                    country=event_handoff.countries[0] if event_handoff.countries else "global",
                    site_relevance_score=rel_result.site_relevance_score,
                    opportunity_score=rel_result.site_relevance_score * 0.20,
                    confidence_score=90.0,
                    status=OpportunityStatus.REJECTED.value,
                    recommended_action=ContentAction.REJECT.value,
                    reasoning_summary=rel_result.rejection_reason,
                    score_reasons=[f"- {rel_result.rejection_reason}"],
                )
                session.add(rejected_opp)
                await session.flush()
                return []

            # 3. Stage 2: Keyword Discovery & Query Expansion
            candidates = self.keyword_expander.discover_and_expand(
                event_title=event_handoff.canonical_title,
                event_summary=event_handoff.summary,
                entities=event_handoff.entities,
                event_type=event_handoff.event_type,
                category=event_handoff.category,
                trend_score=event_handoff.trend_score,
                velocity_score=event_handoff.velocity_score,
                language=event_handoff.language,
                country=event_handoff.countries[0] if event_handoff.countries else "global",
            )

            if not candidates:
                logger.warning("no_keyword_candidates_discovered", event_id=event_handoff.event_id)
                return []

            # Persist or update discovered keywords in DB
            db_keywords: dict[str, Keyword] = {}
            for cand in candidates:
                kw_stmt = select(Keyword).where(
                    Keyword.normalized_keyword == cand.normalized_keyword,
                    Keyword.language == event_handoff.language,
                    Keyword.country == (event_handoff.countries[0] if event_handoff.countries else "global"),
                )
                kw_res = await session.execute(kw_stmt)
                existing_kw = kw_res.scalar_one_or_none()

                if not existing_kw:
                    existing_kw = Keyword(
                        keyword=cand.keyword,
                        normalized_keyword=cand.normalized_keyword,
                        language=event_handoff.language,
                        country=event_handoff.countries[0] if event_handoff.countries else "global",
                        intent=cand.intent.value,
                        intent_confidence=cand.intent_confidence,
                        secondary_intent=cand.secondary_intent.value if cand.secondary_intent else None,
                        search_demand_score=cand.search_demand_score,
                        # STRICT: Null volume and cpc
                        search_volume=cand.search_volume,
                        search_volume_source=cand.search_volume_source,
                        cpc=cand.cpc,
                        cpc_currency=cand.cpc_currency,
                        trend_direction=cand.trend_direction,
                        freshness_sensitivity=cand.freshness_sensitivity.value,
                        commercial_value_score=cand.commercial_value_score,
                        metadata_json=cand.provenance,
                    )
                    session.add(existing_kw)
                    await session.flush()
                db_keywords[cand.normalized_keyword] = existing_kw

            # 4. Stage 3: Keyword Clustering
            clusters = self.clustering_engine.cluster(
                keywords=candidates,
                language=event_handoff.language,
                country=event_handoff.countries[0] if event_handoff.countries else "global",
            )

            # 5. Load Existing Site Content for Cannibalization Check
            content_stmt = select(SiteContent).where(SiteContent.site_id == site.id)
            content_res = await session.execute(content_stmt)
            existing_articles = list(content_res.scalars().all())

            # 6. Analyze Top Promising Clusters (Funnel: Top 3 clusters max)
            top_clusters = clusters[:3]
            packages: list[ContentOpportunityPackage] = []

            for cluster in top_clusters:
                # Save KeywordCluster in DB
                kw_cluster = KeywordCluster(
                    canonical_topic=cluster.canonical_topic,
                    primary_keyword=cluster.primary_keyword,
                    primary_intent=cluster.primary_intent.value,
                    language=cluster.language,
                    country=cluster.country,
                    keyword_count=len(cluster.members),
                    aggregate_demand_score=cluster.aggregate_demand_score,
                    commercial_value_score=cluster.commercial_value_score,
                    freshness_score=cluster.freshness_score,
                    cluster_confidence=cluster.cluster_confidence,
                )
                session.add(kw_cluster)
                await session.flush()

                # Add member associations
                for m in cluster.members:
                    db_kw = db_keywords.get(m.keyword.normalized_keyword)
                    if db_kw:
                        mem = KeywordClusterMember(
                            cluster_id=kw_cluster.id,
                            keyword_id=db_kw.id,
                            is_primary=m.is_primary,
                            similarity_score=m.similarity_score,
                        )
                        session.add(mem)

                # Fetch SERP Snapshot for the primary cluster query
                serp_data = await self.serp_provider.search(
                    query=cluster.primary_keyword,
                    country=cluster.country,
                    language=cluster.language,
                )

                # Persist SERPSnapshot & Results
                db_serp = SERPSnapshot(
                    query=serp_data.query,
                    query_hash=serp_data.query_hash,
                    provider=serp_data.provider,
                    country=serp_data.country,
                    language=serp_data.language,
                    device=serp_data.device,
                    total_results_estimate=serp_data.total_results_estimate,
                    features=serp_data.features,
                    dominant_intent=serp_data.dominant_intent.value,
                    intent_alignment_score=serp_data.intent_alignment_score,
                    retrieved_at=serp_data.retrieved_at,
                    expires_at=datetime.now(UTC) + timedelta(days=7),
                    cost_usd=serp_data.cost_usd,
                )
                session.add(db_serp)
                await session.flush()

                for r in serp_data.results:
                    db_r = SERPResult(
                        snapshot_id=db_serp.id,
                        position=r.position,
                        url=r.url,
                        domain=r.domain,
                        title=r.title,
                        snippet=r.snippet,
                        result_type=r.result_type.value,
                        published_date=r.published_date,
                        is_official_domain=r.is_official_domain,
                        is_forum=r.is_forum,
                        features=r.features,
                    )
                    session.add(db_r)

                # SERP & Competition Analysis
                serp_analysis = self.serp_analyzer.analyze(serp_data)
                comp_analysis = self.competition_analyzer.analyze(serp_data)

                # Cannibalization Check against Existing Site Articles
                cann_result = self.cannibalization_detector.evaluate(
                    candidate_keyword=cluster.primary_keyword,
                    candidate_intent=cluster.primary_intent,
                    candidate_topic=cluster.canonical_topic,
                    existing_articles=existing_articles,
                )

                # 7. Generate Diverse Publishing Angles for this Topic
                angles = self.angle_generator.generate_angles(
                    canonical_topic=cluster.canonical_topic,
                    event_title=event_handoff.canonical_title,
                    category=event_handoff.category,
                    entities=event_handoff.entities,
                    trend_score=event_handoff.trend_score,
                    site_audiences=site.target_audiences,
                )

                # Score each angle and select the strongest angle for this cluster
                best_score = -1.0
                best_scoring_res = None
                best_angle = None

                for angle in angles:
                    # Calculate expiration if breaking
                    expires_at = None
                    if angle.freshness_decay_type.value == "fast_decay":
                        expires_at = datetime.now(UTC) + timedelta(hours=12)

                    scoring_input = ScoringInput(
                        trend_score=event_handoff.trend_score,
                        search_demand_score=cluster.aggregate_demand_score,
                        intent_strength_score=85.0,
                        competition_opportunity_score=comp_analysis.competition_opportunity_score,
                        site_relevance_score=rel_result.site_relevance_score,
                        topical_authority_score=rel_result.topical_authority_score,
                        freshness_score=angle.freshness_score,
                        evergreen_score=angle.evergreen_score,
                        original_value_score=comp_analysis.original_value_score,
                        serp_gap_score=comp_analysis.serp_gap_score,
                        monetization_score=cluster.commercial_value_score,
                        audience_fit_score=angle.audience_fit_score,
                        cannibalization_risk_score=cann_result.cannibalization_risk_score,
                        risk_score=50.0 if event_handoff.risk_flags else 0.0,
                        is_official_dominant=serp_analysis.official_domain_dominant,
                        evidence_count=len(comp_analysis.gaps) + len(serp_data.results),
                        recommended_action=cann_result.recommended_action,
                        expires_at=expires_at,
                        scoring_profile=angle.scoring_profile,
                    )

                    score_res = self.scoring_engine.score(scoring_input)

                    if score_res.opportunity_score > best_score:
                        best_score = score_res.opportunity_score
                        best_scoring_res = score_res
                        best_angle = angle

                if best_angle and best_scoring_res:
                    # Expiration window
                    expires_at = None
                    if best_angle.freshness_decay_type.value == "fast_decay":
                        expires_at = datetime.now(UTC) + timedelta(hours=12)

                    # Create ContentOpportunity entity
                    opp = ContentOpportunity(
                        event_id=event_uuid,
                        site_id=site.id,
                        canonical_topic=cluster.canonical_topic,
                        proposed_angle=best_angle.proposed_angle,
                        working_title=best_angle.working_title,
                        primary_keyword=cluster.primary_keyword,
                        primary_intent=best_angle.primary_intent.value,
                        secondary_intent=best_angle.secondary_intent.value if best_angle.secondary_intent else None,
                        content_type=best_angle.content_type.value,
                        target_audience=best_angle.target_audience,
                        language=cluster.language,
                        country=cluster.country,
                        cluster_role=best_angle.cluster_role.value,
                        recommended_action=cann_result.recommended_action.value,
                        target_content_id=cann_result.target_content_id,
                        trend_score=event_handoff.trend_score,
                        search_demand_score=cluster.aggregate_demand_score,
                        intent_strength_score=85.0,
                        competition_score=comp_analysis.competition_score,
                        competition_opportunity_score=comp_analysis.competition_opportunity_score,
                        freshness_score=best_angle.freshness_score,
                        evergreen_score=best_angle.evergreen_score,
                        site_relevance_score=rel_result.site_relevance_score,
                        topical_authority_score=rel_result.topical_authority_score,
                        original_value_score=comp_analysis.original_value_score,
                        information_gain_score=comp_analysis.information_gain_score,
                        serp_gap_score=comp_analysis.serp_gap_score,
                        monetization_score=cluster.commercial_value_score,
                        audience_fit_score=best_angle.audience_fit_score,
                        content_type_fit_score=best_angle.content_type_fit_score,
                        cannibalization_risk_score=cann_result.cannibalization_risk_score,
                        risk_score=50.0 if event_handoff.risk_flags else 0.0,
                        opportunity_score=best_scoring_res.opportunity_score,
                        confidence_score=best_scoring_res.confidence_score,
                        scoring_profile=best_scoring_res.scoring_profile,
                        score_breakdown=best_scoring_res.score_breakdown,
                        penalties_breakdown=best_scoring_res.penalties_breakdown,
                        score_reasons=best_scoring_res.score_explanation,
                        status=best_scoring_res.status.value,
                        priority=best_scoring_res.priority.value,
                        reasoning_summary=cann_result.rationale,
                        risk_flags=event_handoff.risk_flags,
                        freshness_decay_type=best_angle.freshness_decay_type.value,
                        expires_at=expires_at,
                        scoring_version="1.0.0",
                        analysis_version="1.0.0",
                        analysis_depth=depth.value,
                    )
                    session.add(opp)
                    await session.flush()

                    # Save ContentGaps
                    for gap in comp_analysis.gaps:
                        db_gap = ContentGap(
                            keyword_cluster_id=kw_cluster.id,
                            opportunity_id=opp.id,
                            gap_type=gap.gap_type,
                            description=gap.description,
                            evidence=gap.evidence,
                            importance_score=gap.importance_score,
                            confidence_score=gap.confidence_score,
                            source_count=len(gap.evidence.get("analyzed_urls", [])),
                        )
                        session.add(db_gap)

                    # Save Discovered Questions
                    for q in serp_analysis.discovered_questions:
                        db_q = DiscoveredQuestion(
                            question=q,
                            normalized_question=self.keyword_expander.normalize(q),
                            intent=cluster.primary_intent.value,
                            keyword_cluster_id=kw_cluster.id,
                            opportunity_id=opp.id,
                            importance_score=80.0,
                            source="serp_paa",
                            confidence=0.95,
                        )
                        session.add(db_q)

                    # Save Opportunity Snapshot for ML auditing
                    snap = OpportunitySnapshot(
                        opportunity_id=opp.id,
                        opportunity_score=opp.opportunity_score,
                        confidence_score=opp.confidence_score,
                        status=opp.status,
                        search_demand_score=opp.search_demand_score,
                        competition_score=opp.competition_score,
                        trend_score=opp.trend_score,
                        freshness_score=opp.freshness_score,
                        evergreen_score=opp.evergreen_score,
                        monetization_score=opp.monetization_score,
                        cannibalization_risk_score=opp.cannibalization_risk_score,
                        snapshot_json={
                            "working_title": opp.working_title,
                            "recommended_action": opp.recommended_action,
                            "score_breakdown": opp.score_breakdown,
                        },
                    )
                    session.add(snap)

                    # If WATCH status, add to Watchlist
                    if opp.status == OpportunityStatus.WATCH.value:
                        watch = OpportunityWatchlist(
                            opportunity_id=opp.id,
                            reason="Emerging topic requires developing evidence or official confirmation.",
                            recheck_after=datetime.now(UTC) + timedelta(hours=6),
                            is_active=True,
                        )
                        session.add(watch)

                    # If qualified for Part 4 handoff
                    if (
                        opp.opportunity_score >= settings.MIN_OPPORTUNITY_SCORE_FOR_HANDOFF
                        and opp.confidence_score >= settings.MIN_OPPORTUNITY_CONFIDENCE_FOR_HANDOFF
                        and opp.status != OpportunityStatus.REJECTED.value
                    ):
                        sec_kws = [m.keyword.keyword for m in cluster.members if not m.is_primary]
                        pkg = build_opportunity_package(
                            opportunity=opp,
                            secondary_keywords=sec_kws[:5],
                            questions=serp_analysis.discovered_questions[:5],
                            entities=[e.get("name", "") for e in event_handoff.entities[:6]],
                            content_gaps=[g.description for g in comp_analysis.gaps],
                            competitor_urls=comp_analysis.competitor_urls,
                            existing_related_content=cann_result.existing_related_content,
                        )
                        packages.append(pkg)

            await session.commit()
            return packages
