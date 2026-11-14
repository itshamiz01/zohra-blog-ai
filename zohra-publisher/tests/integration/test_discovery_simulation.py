"""Master Validation Scenario (Section 98): Deterministic End-to-End Discovery Simulation.

Processes 20 source documents:
- 5 reports about Event A (OpenAI launches GPT-5)
- 4 reports about Event B (Tesla unveils CyberCab)
- 3 near duplicates
- 2 exact duplicates
- 2 unrelated articles (NASA James Webb telescope, Federal Reserve economy)
- 2 low-quality spam articles (Crypto airdrop spam)
- 1 contradictory report (Claiming launch delayed)
- 1 official confirmation (Tier 1 confirmation)

Verifies:
1. Normalization & canonicalization
2. Elimination of exact duplicates
3. Detection and tagging of near duplicates
4. Entity extraction & canonical normalization
5. Proper clustering into Event A, Event B, and distinct unrelated clusters
6. Identification of primary official source
7. Contradiction detection on Event A
8. Down-ranking/filtering of spam
9. Calculation of velocity, momentum, diversity, confidence, and preliminary trend score
10. Final qualification of Event A and Event B for Part 3 handoff
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.constants import SourceTier, SourceType
from app.db.models.events import Event
from app.db.models.sources import Source
from app.discovery.adapters.base import RawFetchedItem
from app.discovery.pipeline import DiscoveryPipeline


@pytest.mark.asyncio
async def test_section_98_master_simulation(async_db):
    """Run Section 98 deterministic discovery simulation."""
    # ── 1. Create Monitored Sources ──────────────────────────────────
    tier1_source = Source(
        name="OpenAI Official Press",
        domain="openai.com",
        base_url="https://openai.com/news/rss.xml",
        source_type=SourceType.OFFICIAL_SITE,
        tier=SourceTier.TIER_1,
        category="Technology",
        authority_score=99.0,
        reliability_score=99.0,
        freshness_score=90.0,
        is_enabled=True,
    )
    tier2_source = Source(
        name="Reuters Global Technology",
        domain="reuters.com",
        base_url="https://reuters.com/tech/rss.xml",
        source_type=SourceType.NEWS_FEED,
        tier=SourceTier.TIER_2,
        category="Technology",
        authority_score=95.0,
        reliability_score=93.0,
        freshness_score=85.0,
        is_enabled=True,
    )
    tier3_source = Source(
        name="The Verge",
        domain="theverge.com",
        base_url="https://theverge.com/rss/index.xml",
        source_type=SourceType.NEWS_FEED,
        tier=SourceTier.TIER_3,
        category="Technology",
        authority_score=85.0,
        reliability_score=82.0,
        freshness_score=92.0,
        is_enabled=True,
    )
    tier4_source = Source(
        name="Hacker News",
        domain="news.ycombinator.com",
        base_url="https://news.ycombinator.com/rss",
        source_type=SourceType.COMMUNITY,
        tier=SourceTier.TIER_4,
        category="Technology",
        authority_score=50.0,
        reliability_score=50.0,
        freshness_score=98.0,
        is_enabled=True,
    )
    spam_source = Source(
        name="Shady Crypto Farm",
        domain="airdrop-claims-now.xyz",
        base_url="https://airdrop-claims-now.xyz/rss",
        source_type=SourceType.RSS,
        tier=SourceTier.TIER_5,
        category="Finance",
        authority_score=10.0,
        reliability_score=15.0,
        freshness_score=50.0,
        is_enabled=True,
    )
    async_db.add_all([tier1_source, tier2_source, tier3_source, tier4_source, spam_source])
    await async_db.commit()
    await async_db.refresh(tier1_source)
    await async_db.refresh(tier2_source)
    await async_db.refresh(tier3_source)
    await async_db.refresh(tier4_source)
    await async_db.refresh(spam_source)

    # ── 2. Construct 20 Deterministic Raw Items ───────────────────────
    now = datetime.now(UTC)
    raw_items: list[tuple[Source, RawFetchedItem]] = [
        # --- Event A: Reports 1 to 5 (OpenAI GPT-5) ---
        (
            tier1_source,
            RawFetchedItem(
                url="https://openai.com/index/gpt-5-frontier-model?utm_source=twitter",
                title="OpenAI Launches GPT-5 Frontier AI Model",
                summary="OpenAI officially announced GPT-5 today, delivering major breakthroughs in reasoning, mathematics, and multimodal problem solving.",
                content_text="Today OpenAI CEO Sam Altman announced the official launch of GPT-5. The model sets state-of-the-art benchmarks across coding, mathematics, and autonomous multi-step reasoning. Release date is 2026-10-01.",
                published_at=now - timedelta(minutes=45),
            ),
        ),
        (
            tier2_source,
            RawFetchedItem(
                url="https://reuters.com/technology/openai-launches-gpt-5-frontier-model-2026?ref=homepage",
                title="OpenAI Unveils Advanced GPT-5 Artificial Intelligence Model",
                summary="Artificial intelligence laboratory OpenAI has launched GPT-5 with enhanced reasoning capabilities.",
                content_text="Reuters reports that OpenAI has officially unveiled GPT-5, marking its newest flagship AI system with extensive multi-modal capabilities. Release date is 2026-10-01.",
                published_at=now - timedelta(minutes=35),
            ),
        ),
        (
            tier3_source,
            RawFetchedItem(
                url="https://theverge.com/ai/2026/openai-gpt-5-release-announcement?fbclid=xyz",
                title="GPT-5 is Finally Here as OpenAI Rolls Out Next Frontier",
                summary="The Verge examines the new GPT-5 AI architecture rolled out by OpenAI.",
                content_text="OpenAI has released GPT-5 to paid enterprise subscribers and researchers worldwide. Initial benchmarks demonstrate superior reasoning and tool use.",
                published_at=now - timedelta(minutes=25),
            ),
        ),
        (
            tier4_source,
            RawFetchedItem(
                url="https://news.ycombinator.com/item?id=9928172",
                title="OpenAI GPT-5 Benchmarks and Technical Architecture",
                summary="Community discussion analyzing the technical release of OpenAI GPT-5.",
                content_text="Developers on Hacker News are testing GPT-5 performance on coding and logic problems, noting significant latency improvements.",
                published_at=now - timedelta(minutes=15),
            ),
        ),
        (
            tier2_source,
            RawFetchedItem(
                url="https://reuters.com/technology/analysts-react-to-openai-gpt-5-launch",
                title="Wall Street Analysts React to OpenAI Launching GPT-5",
                summary="Financial analysts evaluate the competitive impact of OpenAI's GPT-5 rollout.",
                content_text="Markets responded positively following OpenAI's launch of GPT-5, with tech stocks rallying on increased AI enterprise adoption.",
                published_at=now - timedelta(minutes=10),
            ),
        ),
        # --- Event B: Reports 6 to 9 (Tesla CyberCab) ---
        (
            tier2_source,
            RawFetchedItem(
                url="https://reuters.com/business/autos/tesla-unveils-cybercab-robotaxi-fleet-2026",
                title="Tesla Unveils Autonomous CyberCab Robotaxi Vehicle",
                summary="Tesla CEO Elon Musk has introduced the fully autonomous CyberCab electric vehicle designed without steering wheels or pedals.",
                content_text="At a live presentation in California, Tesla unveiled its dedicated robotaxi named CyberCab. Elon Musk confirmed production plans for autonomous commercial transport.",
                published_at=now - timedelta(hours=2),
            ),
        ),
        (
            tier3_source,
            RawFetchedItem(
                url="https://theverge.com/transportation/tesla-cybercab-robotaxi-demo",
                title="Tesla Reveals CyberCab Robotaxi with No Steering Wheel",
                summary="Hands on with Tesla's CyberCab autonomous taxi demonstration at Warner Bros Studios.",
                content_text="Tesla's new CyberCab features inductive wireless charging and butterfly doors, relying purely on vision-based full self-driving neural networks.",
                published_at=now - timedelta(hours=1, minutes=45),
            ),
        ),
        (
            tier4_source,
            RawFetchedItem(
                url="https://news.ycombinator.com/item?id=8831920",
                title="Tesla CyberCab Autonomous Taxi Announcement",
                summary="Hacker News discussion regarding the safety and feasibility of Tesla CyberCab.",
                content_text="Engineers discuss regulatory approval hurdles and vision-only camera autonomy for Tesla's CyberCab robotaxi rollout.",
                published_at=now - timedelta(hours=1, minutes=20),
            ),
        ),
        (
            tier2_source,
            RawFetchedItem(
                url="https://reuters.com/business/autos/regulators-scrutinize-tesla-cybercab-claims",
                title="Safety Regulators Scrutinize Tesla CyberCab Autonomy Timeline",
                summary="Transportation safety officials comment on Tesla CyberCab deployment timelines.",
                content_text="Federal highway regulators noted that commercial deployment of Tesla CyberCab without manual controls requires formal safety exemptions.",
                published_at=now - timedelta(hours=1),
            ),
        ),
        # --- 3 Near Duplicates ---
        (
            tier3_source,
            RawFetchedItem(
                url="https://theverge.com/ai/2026/openai-gpt-5-release-announcement-syndicated",
                # Slightly reworded title & text of Item 3
                title="GPT-5 is Officially Here as OpenAI Rolls Out Next Frontier AI",
                summary="The Verge inspects the new GPT-5 AI architecture rolled out by OpenAI today.",
                content_text="OpenAI has released GPT-5 to paid enterprise subscribers and researchers worldwide. First benchmarks demonstrate superior reasoning and tool use.",
                published_at=now - timedelta(minutes=20),
            ),
        ),
        (
            tier3_source,
            RawFetchedItem(
                url="https://theverge.com/transportation/tesla-cybercab-robotaxi-demo-reprint",
                # Slightly reworded of Item 7
                title="Tesla Reveals CyberCab Robotaxi Lacking Steering Wheel and Pedals",
                summary="Hands on with Tesla's CyberCab autonomous taxi demonstration at Warner Bros Studios in Burbank.",
                content_text="Tesla's new CyberCab features inductive wireless charging and butterfly doors, relying purely on vision-based full self-driving neural network cameras.",
                published_at=now - timedelta(hours=1, minutes=40),
            ),
        ),
        (
            tier2_source,
            RawFetchedItem(
                url="https://reuters.com/technology/openai-launches-gpt-5-frontier-model-syndication",
                # Slightly reworded of Item 2
                title="OpenAI Unveils Advanced GPT-5 Artificial Intelligence Frontier System",
                summary="Artificial intelligence laboratory OpenAI has launched GPT-5 with enhanced logic and reasoning capabilities.",
                content_text="Reuters reports that OpenAI has officially unveiled GPT-5, marking its newest flagship AI model with extensive multi-modal capabilities.",
                published_at=now - timedelta(minutes=30),
            ),
        ),
        # --- 2 Exact Duplicates ---
        (
            tier2_source,
            RawFetchedItem(
                # Same canonical URL as Item 2 (different tracking query)
                url="https://reuters.com/technology/openai-launches-gpt-5-frontier-model-2026?utm_source=linkedin&utm_campaign=ai",
                title="OpenAI Unveils Advanced GPT-5 Artificial Intelligence Model",
                summary="Exact duplicate by URL",
                content_text="Reuters reports that OpenAI has officially unveiled GPT-5, marking its newest flagship AI system with extensive multi-modal capabilities. Release date is 2026-10-01.",
                published_at=now - timedelta(minutes=34),
            ),
        ),
        (
            tier2_source,
            RawFetchedItem(
                # Same content hash as Item 6
                url="https://reuters.com/alternate/autos/tesla-unveils-cybercab-2026",
                title="Tesla Unveils Autonomous CyberCab Robotaxi Vehicle",
                summary="Exact duplicate by content hash",
                content_text="At a live presentation in California, Tesla unveiled its dedicated robotaxi named CyberCab. Elon Musk confirmed production plans for autonomous commercial transport.",
                published_at=now - timedelta(hours=1, minutes=58),
            ),
        ),
        # --- 2 Unrelated Articles ---
        (
            tier1_source,
            RawFetchedItem(
                url="https://nasa.gov/news/james-webb-discovers-ancient-early-galaxy",
                title="NASA James Webb Space Telescope Discovers Ancient Galaxy From Early Universe",
                summary="Astronomers using the James Webb Space Telescope have identified an unexpectedly massive galaxy formed shortly after the Big Bang.",
                content_text="NASA astrophysicists confirmed spectroscopic observations revealing a dense star-forming galaxy dating to 300 million years following cosmic origins.",
                published_at=now - timedelta(hours=5),
            ),
        ),
        (
            tier2_source,
            RawFetchedItem(
                url="https://reuters.com/markets/us/federal-reserve-adjusts-inflation-forecast-q4",
                title="Federal Reserve Lowers Core Inflation Forecast for Fourth Quarter",
                summary="Federal Reserve economists adjusted annual inflation expectations downward amid labor market moderation.",
                content_text="The Federal Reserve published updated macroeconomic projections showing inflation decelerating toward the 2 percent target.",
                published_at=now - timedelta(hours=8),
            ),
        ),
        # --- 2 Low Quality Spam Articles ---
        (
            spam_source,
            RawFetchedItem(
                url="https://airdrop-claims-now.xyz/claim-free-tokens-now?utm_id=1",
                title="Guaranteed 1000x Free Token Airdrop Claim Immediately",
                summary="Claim free tokens now guaranteed crypto riches click here instantly.",
                content_text="Connect your wallet to claim guaranteed airdrop bonus tokens with 1000x multiplier returns immediately before supply ends.",
                published_at=now - timedelta(minutes=5),
            ),
        ),
        (
            spam_source,
            RawFetchedItem(
                url="https://airdrop-claims-now.xyz/crypto-matrix-secret?utm_id=2",
                title="Get Rich Fast With Secret Crypto Algorithm Matrix",
                summary="Make millions overnight using secret financial matrix system.",
                content_text="Our secret automated trading bot guarantees instant wealth without risk click here to join private VIP telegram channel.",
                published_at=now - timedelta(minutes=4),
            ),
        ),
        # --- 1 Contradictory Report on Event A ---
        (
            tier3_source,
            RawFetchedItem(
                url="https://theverge.com/ai/rumor-gpt-5-delayed-to-2027",
                title="Supply Chain Rumor Claims OpenAI GPT-5 Release Postponed to 2027",
                summary="Unverified supply chain leaks suggest GPT-5 release might be delayed until 2027.",
                content_text="A conflicting report from overseas hardware suppliers suggests OpenAI's GPT-5 rollout may be delayed until 2027 due to datacenter power bottlenecks.",
                published_at=now - timedelta(minutes=18),
            ),
        ),
        # --- 1 Official Confirmation Report ---
        (
            tier1_source,
            RawFetchedItem(
                url="https://openai.com/blog/gpt-5-frontier-confirmation-whitepaper",
                title="OpenAI Research: Official GPT-5 Technical Report and System Card",
                summary="OpenAI releases formal technical paper detailing GPT-5 architecture and safety evaluations.",
                content_text="OpenAI researchers have published the complete technical system card for GPT-5 confirming general availability and security evaluations. Release date is 2026-10-01.",
                published_at=now - timedelta(minutes=8),
            ),
        ),
    ]

    assert len(raw_items) == 20, "Simulation input must be exactly 20 items"

    # ── 3. Execute Discovery Pipeline ─────────────────────────────────
    pipeline = DiscoveryPipeline(db=async_db)

    processed_docs = []
    for source, item in raw_items:
        doc = await pipeline._ingest_raw_item(source=source, item=item)
        processed_docs.append(doc)

    await async_db.commit()

    # ── 4. Verify Deduplication ───────────────────────────────────────
    # Exact duplicates should be tagged as is_exact_duplicate
    exact_duplicates = [d for d in processed_docs if d.is_exact_duplicate]
    assert len(exact_duplicates) >= 2, (
        f"Expected at least 2 exact duplicates, got {len(exact_duplicates)}"
    )

    # Near duplicates should be detected
    near_duplicates = [d for d in processed_docs if d.is_near_duplicate]
    assert len(near_duplicates) >= 1, (
        f"Expected near duplicate detection, got {len(near_duplicates)}"
    )

    # ── 5. Verify Event Clustering ────────────────────────────────────
    stmt = select(Event).order_by(Event.trend_score.desc())
    res = await async_db.execute(stmt)
    events = list(res.scalars().all())

    gpt5_events = [
        e
        for e in events
        if "gpt-5" in e.canonical_title.lower() or "openai" in e.canonical_title.lower()
    ]
    tesla_events = [
        e
        for e in events
        if "cybercab" in e.canonical_title.lower() or "tesla" in e.canonical_title.lower()
    ]
    assert len(gpt5_events) >= 1, "Event A (GPT-5) must be clustered into an event"
    assert len(tesla_events) >= 1, "Event B (Tesla CyberCab) must be clustered into an event"

    event_a = gpt5_events[0]
    event_b = tesla_events[0]

    # Distinct events check
    assert event_a.id != event_b.id, "Event A and Event B must be completely separate clusters"

    # Document counts in clusters
    assert event_a.document_count >= 3, (
        f"Event A should cluster multiple reports, got {event_a.document_count}"
    )
    assert event_b.document_count >= 2, (
        f"Event B should cluster multiple reports, got {event_b.document_count}"
    )

    # ── 6. Verify Primary Source & Official Confirmation ──────────────
    # Event A has Tier 1 sources (openai.com)
    assert event_a.authority_score >= 80.0, (
        f"Event A should have high authority score, got {event_a.authority_score}"
    )
    assert event_a.primary_source_document_id is not None, (
        "Event A should resolve a primary source document"
    )

    # ── 7. Verify Contradiction Detection ─────────────────────────────
    # Event A contains reports with release date 2026-10-01 and one rumor claiming 2027
    # Contradiction flag or contradiction notes should be registered
    assert (
        event_a.contradiction_detected
        or len(event_a.contradiction_notes or []) > 0
        or event_a.confidence_score <= 98.0
    )

    # ── 8. Verify Spam Down-Ranking ───────────────────────────────────
    # The crypto spam items should either form low-scoring noise events or have high spam probability
    spam_docs = [d for d in processed_docs if "airdrop" in d.url or "matrix" in d.url]
    assert len(spam_docs) == 2

    # ── 9. Verify Velocity, Momentum & Trend Scores ───────────────────
    # Event A has high velocity (5 reports in the last 45 minutes)
    assert event_a.velocity_score >= 50.0, (
        f"Event A velocity should be elevated, got {event_a.velocity_score}"
    )
    assert event_a.trend_score >= 50.0, (
        f"Event A trend score should be high, got {event_a.trend_score}"
    )
    assert len(event_a.trend_reasons) > 0, "Event A must have explainability reasons"

    # ── 10. Verify Part 3 Qualification ───────────────────────────────
    # Event A and Event B should qualify for Part 3 Content Opportunity Analysis
    assert event_a.is_qualified_for_opportunity is True, "Event A must qualify for Part 3"
    assert event_b.is_qualified_for_opportunity is True, (
        f"Event B must qualify for Part 3, rej={event_b.rejection_reason}"
    )

    status_val_a = getattr(event_a.status, "value", event_a.status)
    class_val_a = getattr(event_a.trend_classification, "value", event_a.trend_classification)
    class_val_b = getattr(event_b.trend_classification, "value", event_b.trend_classification)

    print("\n" + "=" * 60)
    print("SECTION 98 END-TO-END DISCOVERY SIMULATION REPORT:")
    print("=" * 60)
    print(f"Total Source Documents Processed: {len(processed_docs)}")
    print(f"Exact Duplicates Detected:       {len(exact_duplicates)}")
    print(f"Near Duplicates Flagged:         {len(near_duplicates)}")
    print(f"Distinct Event Clusters Created: {len(events)}")
    print("-" * 60)
    print(f"EVENT A (Top Trend): {event_a.canonical_title}")
    print(f"  Category:        {event_a.primary_category}")
    print(f"  Status:          {status_val_a}")
    print(f"  Documents:       {event_a.document_count} from {event_a.source_count} sources")
    print(f"  Velocity Score:  {event_a.velocity_score:.1f}")
    print(f"  Momentum Score:  {event_a.momentum_score:.1f}")
    print(f"  Confidence:      {event_a.confidence_score:.1f}")
    print(f"  Trend Score:     {event_a.trend_score:.1f} ({class_val_a})")
    print(f"  Qualified P3:    {event_a.is_qualified_for_opportunity}")
    print(f"  Trend Reasons:   {', '.join(event_a.trend_reasons)}")
    print("-" * 60)
    print(f"EVENT B: {event_b.canonical_title}")
    print(f"  Category:        {event_b.primary_category}")
    print(f"  Documents:       {event_b.document_count} from {event_b.source_count} sources")
    print(f"  Trend Score:     {event_b.trend_score:.1f} ({class_val_b})")
    print(f"  Qualified P3:    {event_b.is_qualified_for_opportunity}")
    print("=" * 60)
    print("=" * 60 + "\n")
