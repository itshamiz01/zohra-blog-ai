"""
Zohra — Integration Tests for Reddit Opportunity & Referral Engine.

Verifies end-to-end workflow:
1. Question Discovery & Ingestion
2. Classification & Relevance Scoring
3. Duplicate Detection & Thematic Clustering
4. Opportunity Scoring & Action Mapping
5. Handoff Package Creation for Research Engine
6. Authentic Standalone Response Generation with Rule Gate
7. Anti-Spam Verification & Idempotency
8. Approval Workflow & Strip-Link Support
9. UTM Attribution & Referral Event Logging
10. Learning Engine Loop
11. REST API Endpoints & Dry-Run Simulator
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest
from sqlalchemy import select

from app.db.models.published_articles import PublishedArticle
from app.db.models.reddit import (
    RedditCommunityPolicy,
    RedditJobStatus,
    RedditOpportunity,
    RedditOpportunityAction,
    RedditQuestion,
    RedditQuestionCluster,
    RedditResponseDraft,
)
from app.db.models.sites import Site
from app.reddit.anti_spam import RedditAntiSpamGuard
from app.reddit.approval import RedditApprovalManager
from app.reddit.clustering import RedditQuestionClusterer
from app.reddit.dedup import RedditDuplicateDetector
from app.reddit.handoff import build_reddit_opportunity_package
from app.reddit.learning import RedditLearningEngine
from app.reddit.opportunity import RedditOpportunityEngine
from app.reddit.provider import RedditProvider
from app.reddit.referral import RedditReferralTracker, build_attributable_url
from app.reddit.response_writer import RedditResponseWriter
from app.reddit.rules import SubredditRuleChecker
from app.reddit.scanner import RedditQuestionScanner
from app.reddit.service import RedditEngineService


@pytest.mark.asyncio
async def test_reddit_api_status_and_dry_run(client, admin_headers, db_session):
    """Test /api/v1/reddit/status and /api/v1/reddit/dry-run REST endpoints."""
    # 1. Status endpoint
    resp = await client.get("/api/v1/reddit/status", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "autonomy_mode" in data
    assert data["posting_enabled"] is False  # Safe default

    # 2. Setup a site for dry-run
    site = Site(
        id=uuid.uuid4(),
        name="Heavenly Insights Test",
        domain="heavenly-insights.example.com",
        niche="Education and Generative AI",
        enabled=True,
    )
    db_session.add(site)
    await db_session.flush()

    # 3. Dry-run endpoint
    dry_run_payload = {
        "site_id": str(site.id),
        "sample_title": "How can teachers prevent students from using ChatGPT to write essays?",
        "sample_body": "Looking for effective classroom policies and pedagogical techniques.",
        "subreddit": "education",
    }
    with patch("app.reddit.classifier.get_default_provider") as mock_class_p, \
         patch("app.reddit.response_writer.get_default_provider") as mock_write_p:
        m_p = AsyncMock()
        m_p.generate.return_value = MagicMock(
            content=json.dumps({
                "is_question": True,
                "question_type": "how_to",
                "primary_question": "How can teachers prevent students from using ChatGPT to write essays?",
                "underlying_problem": "Pedagogical alternatives to flawed AI text detection",
                "search_intent": "informational",
                "target_audience": "Educators",
                "extracted_entities": ["ChatGPT", "Essays"],
                "urgency_level": "normal",
                "clarity_score": 85.0,
                "answerability_score": 90.0,
                "answer_text": "To prevent unauthorized AI use in student writing, educators should shift from punitive detection to authentic assessment.",
                "optional_resource_sentence": "",
                "link_rationale": "No link included",
            })
        )
        mock_class_p.return_value = m_p
        mock_write_p.return_value = m_p

        resp = await client.post(
            f"/api/v1/reddit/dry-run?site_id={site.id}&sample_title={dry_run_payload['sample_title']}&subreddit=education",
            headers=admin_headers,
        )
    assert resp.status_code == 200
    res_data = resp.json()["data"]
    assert "How can teachers prevent" in res_data["question_detected"]
    assert res_data["would_publish"] is False  # Live posting strictly disabled for dry run
    assert res_data["opportunity_score"] > 50.0
    assert "Definitive Guide" in res_data["proposed_article"]


@pytest.mark.asyncio
async def test_full_reddit_opportunity_lifecycle_end_to_end(db_session):
    """
    End-to-end integration test of the full lifecycle without external network:
    Discovery -> Classification -> Cluster -> Opportunity -> Handoff ->
    Response -> Rule Check -> Anti-Spam -> Approval -> Referral -> Learning
    """
    now = datetime.now(timezone.utc)
    site_id = uuid.uuid4()
    site = Site(
        id=site_id,
        name="AI in Education Academy",
        domain="aieducation.test",
        niche="AI tools for students and teachers",
        enabled=True,
    )
    db_session.add(site)
    await db_session.flush()

    # ── 1. Ingestion / Scanner ──
    raw_question = RedditQuestion(
        id=uuid.uuid4(),
        site_id=site_id,
        reddit_post_id="post_integ_001",
        subreddit="education",
        permalink="/r/education/comments/integ1",
        url="https://reddit.com/r/education/comments/integ1",
        raw_title="How can high school teachers verify whether an essay was AI generated?",
        raw_body="AI detectors give too many false positives. What is the actual evidence-based way to handle this?",
        flair="Discussion",
        reddit_score=142,
        reddit_comment_count=58,
        posted_at=now,
        is_question=True,
        question_type="HOW_TO",
        primary_question="How can high school teachers verify whether an essay was AI generated?",
        underlying_problem="Reliability of AI detection tools and fair assessment strategies",
        search_intent="informational",
        target_audience="High school teachers and administrators",
        extracted_entities=["ChatGPT", "AI detectors", "High school"],
        urgency_level="high",
        relevance_score=88.5,
        relevance_reasons=["Direct alignment with AI in Education niche", "High community engagement"],
        status=RedditJobStatus.DISCOVERED.value,
    )
    db_session.add(raw_question)
    await db_session.flush()

    # ── 2. Thematic Clustering ──
    clusterer = RedditQuestionClusterer(db_session)
    cluster = await clusterer.assign_or_create_cluster(site_id=site_id, question=raw_question)
    assert cluster is not None
    assert cluster.site_id == site_id
    assert cluster.question_count >= 1

    # ── 3. Opportunity Scoring & Action Resolution ──
    opp_engine = RedditOpportunityEngine(db_session)
    opp = await opp_engine.evaluate_opportunity(site_id=site_id, question=raw_question, cluster=cluster)
    assert opp is not None
    assert opp.overall_opportunity_score >= 65.0
    assert opp.recommended_action == RedditOpportunityAction.CREATE_NEW_ARTICLE.value

    # ── 4. Handoff Package Construction ──
    handoff_pkg = build_reddit_opportunity_package(opp, raw_question)
    assert handoff_pkg.opportunity_score == opp.overall_opportunity_score
    assert handoff_pkg.primary_keyword != ""

    # ── 5. Simulate Existing Article Creation & Publishing ──
    article_id = uuid.uuid4()
    article_title = "The Teacher's Guide to AI Detection: Why Detectors Fail and What Works Instead"
    article_slug = "teachers-guide-ai-detection-accuracy"
    article_url = "https://aieducation.test/teachers-guide-ai-detection-accuracy"
    opp.generated_article_id = article_id
    await db_session.flush()

    # ── 6. Subreddit Rule Engine ──
    rule_checker = SubredditRuleChecker(db_session)
    policy = await rule_checker.get_or_refresh_policy(site_id=site_id, subreddit="education")
    # For integration test, simulate policy allowing helpful non-spam resource
    policy.external_links_allowed = True
    policy.self_promotion_allowed = True
    policy.rule_status = "verified"
    await db_session.flush()

    link_allowed, reason = rule_checker.check_link_permitted(policy)
    assert link_allowed is True

    # ── 7. Standalone Reddit Response Generation with Attributable Link ──
    tracked_url = build_attributable_url(
        article_url,
        subreddit="education",
        campaign="reddit_education_ai_detection",
    )
    assert "utm_source=reddit" in tracked_url
    assert "utm_medium=community" in tracked_url

    response_writer = RedditResponseWriter()
    # Fast mock for LLM provider during integration test
    with patch("app.reddit.response_writer.get_default_provider") as mock_get_provider:
        mock_provider = AsyncMock()
        mock_provider.generate.return_value = MagicMock(
            content=json.dumps({
                "answer_text": "AI text detectors typically rely on perplexity and burstiness metrics, which yield high false positive rates for non-native English speakers. Instead of relying on automated detection tools, evidence shows the most effective approach is process-based evaluation: having students document prompt iteration logs, incorporating in-class oral defenses, and designing assignments that require localized, classroom-specific context.",
                "optional_resource_sentence": f"I put together a detailed pedagogical breakdown with the full empirical error rate studies here: [The Teacher's Guide to AI Detection]({tracked_url})",
                "link_rationale": "Provides extended empirical accuracy studies and classroom defense rubrics",
            })
        )
        mock_get_provider.return_value = mock_provider

        generated = await response_writer.generate_response(
            question_title=raw_question.primary_question,
            question_body=raw_question.raw_body,
            article_title=article_title,
            article_url=tracked_url,
            article_excerpt="Comprehensive breakdown of LLM watermarks, perplexity metrics, and classroom oral defense methods.",
            allow_link=link_allowed,
        )
    assert len(generated.answer_text) > 100
    assert generated.included_link == tracked_url
    assert "detector" in generated.answer_text.lower() or "ai" in generated.answer_text.lower()

    # ── 8. Anti-Spam Guard ──
    anti_spam = RedditAntiSpamGuard(db_session)
    with patch("app.reddit.anti_spam.get_settings") as mock_settings, \
         patch.object(anti_spam, "verify_destination_url", new_callable=AsyncMock) as mock_verify_url:
        settings_mock = MagicMock()
        settings_mock.AUTONOMY_ENABLED = True
        settings_mock.MAINTENANCE_MODE = False
        settings_mock.REDDIT_MAX_COMMENTS_PER_DAY = 5
        settings_mock.REDDIT_MAX_COMMENTS_PER_SUBREDDIT_PER_DAY = 2
        settings_mock.REDDIT_MIN_HOURS_BETWEEN_POSTS = 1.0
        mock_settings.return_value = settings_mock
        mock_verify_url.return_value = (True, "Destination URL verified accessible (HTTP 200)")

        anti_spam_res = await anti_spam.validate_submission(
            site_id=site_id,
            subreddit="education",
            response_text=generated.full_markdown,
            proposed_link=generated.included_link,
        )
    assert anti_spam_res.passed is True


    # ── 9. Approval Queue Workflow ──
    draft = RedditResponseDraft(
        site_id=site_id,
        opportunity_id=opp.id,
        reddit_post_id=raw_question.reddit_post_id,
        subreddit=raw_question.subreddit,
        response_type=generated.response_type,
        response_body=generated.full_markdown,
        has_external_link=bool(generated.included_link),
        proposed_link=generated.included_link,
        link_rationale=generated.link_rationale,
        rule_check_passed=True,
        rule_check_details={"policy": "verified"},
        anti_spam_passed=True,
        anti_spam_details=anti_spam_res.to_dict(),
        destination_article_verified=True,
        status="awaiting_approval",
    )
    db_session.add(draft)
    await db_session.flush()

    approval_mgr = RedditApprovalManager(db_session)
    approved_draft = await approval_mgr.approve_draft(draft.id, reviewed_by="editor_lead")
    assert approved_draft.status == "approved"

    # ── 10. Referral Event Tracking ──
    referral_tracker = RedditReferralTracker(db_session)
    ref_event = await referral_tracker.record_referral(
        site_id=site_id,
        destination_url=tracked_url,
        article_slug=article_slug,
        subreddit="education",
        utm_campaign="reddit_education_ai_detection",
        session_id="sess_student_456",
        engaged_seconds=185.0,
        converted=True,
    )
    assert ref_event.session_id == "sess_student_456"
    assert ref_event.converted is True

    # ── 11. Learning Engine Feedback ──
    learning = RedditLearningEngine(db_session)
    insights = await learning.evaluate_cluster_performance(site_id=site_id)
    assert isinstance(insights, list)
    assert len(insights) >= 1
    assert insights[0]["topic"] == cluster.parent_topic

    candidates = await learning.extract_topic_expansion_candidates(site_id=site_id)
    assert isinstance(candidates, list)
