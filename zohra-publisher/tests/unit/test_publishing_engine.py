"""
Unit tests for Part 7 Publishing Engine:
- PublicationGate & hash integrity
- WordPress Client & secret redaction
- Taxonomy resolution (category equivalence, tag explosion prevention)
- Media planning, rights validation, image optimization
- Internal link candidate resolution & injection
- SEO packaging, slug collision, and schema generation
- Scheduling engine, timezone conversion, publication windows, cadence limits
- Post verification & reconciliation
- HTML rendering & sanitization
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.audit.parser.content_parser import ContentParser
from app.audit.security.token import AuditTokenManager
from app.integrations.wordpress.auth import (
    redact_secrets,
    sanitize_dict_for_logging,
)
from app.publishing.gate import PublicationGate, PublicationGateError
from app.publishing.links import InternalLinkResolver
from app.publishing.media import (
    MediaOptimizer,
    MediaPlanner,
    MediaRightsValidator,
)
from app.publishing.renderer import PublicationRenderer
from app.publishing.scheduler import PublicationScheduler, SchedulingError
from app.publishing.seo import SchemaEngine, SEOPackager
from app.publishing.taxonomy import TaxonomyResolver
from app.publishing.verifier import PostVerifier, VerificationError
from app.schemas.publishing import AssetType, MediaSourceStrategy

# ── 1. Gate & Hash Validation Tests ──────────────────────────────────

def test_publication_gate_valid_hash():
    text = "The rapid evolution of AI agents transforms modern software engineering."
    content_hash = ContentParser.compute_content_hash(text)
    fingerprint = AuditTokenManager.generate_audit_fingerprint(content_hash, 1)
    token = AuditTokenManager.sign_audit_token("draft-1", content_hash, fingerprint, "PASS")

    fap = {
        "decision": "PASS",
        "eligible_for_part7": True,
        "content_hash": content_hash,
        "audit_token": token,
    }

    assert PublicationGate.validate_audit_package(fap, text) is True


def test_publication_gate_rejects_unapproved_decision():
    fap = {
        "decision": "REVISE",
        "eligible_for_part7": False,
        "content_hash": "dummy_hash",
        "audit_token": "dummy_token",
    }
    with pytest.raises(PublicationGateError, match="Audit decision is REVISE"):
        PublicationGate.validate_audit_package(fap, "Article text")


def test_publication_gate_rejects_tampered_hash():
    original_text = "Original audited text."
    tampered_text = "Modified text after audit approval."
    original_hash = ContentParser.compute_content_hash(original_text)
    fingerprint = AuditTokenManager.generate_audit_fingerprint(original_hash, 1)
    token = AuditTokenManager.sign_audit_token("draft-1", original_hash, fingerprint, "PASS")

    fap = {
        "decision": "PASS",
        "eligible_for_part7": True,
        "content_hash": original_hash,
        "audit_token": token,
    }
    with pytest.raises(PublicationGateError, match="Post-audit mutation detected"):
        PublicationGate.validate_audit_package(fap, tampered_text)



# ── 2. Credential Security & Redaction Tests ─────────────────────────

def test_secret_redaction():
    text = "Authorization: Basic dXNlcjpwYXNzd29yZA== and token=secret123"
    redacted = redact_secrets(text)
    assert "dXNlcjpwYXNzd29yZA==" not in redacted
    assert "secret123" not in redacted


def test_sanitize_dict_for_logging():
    data = {
        "title": "Clean Title",
        "app_password": "supersecretpassword",
        "nested": {"token": "bearertoken123", "val": 42},
    }
    safe = sanitize_dict_for_logging(data)
    assert safe["title"] == "Clean Title"
    assert safe["app_password"] == "[REDACTED]"
    assert safe["nested"]["token"] == "[REDACTED]"
    assert safe["nested"]["val"] == 42


# ── 3. Taxonomy Resolution Tests ─────────────────────────────────────

def test_taxonomy_category_resolution():
    categories = [
        {"id": 10, "name": "Artificial Intelligence", "slug": "artificial-intelligence"},
        {"id": 11, "name": "Cloud Computing", "slug": "cloud-computing"},
    ]
    # AI should resolve to ID 10 via equivalence
    cat_id = TaxonomyResolver.resolve_category("AI", categories)
    assert cat_id == 10

    # Unknown category falls back to default
    cat_id_default = TaxonomyResolver.resolve_category("Unknown Niche", categories, default_category_id=1)
    assert cat_id_default == 1


def test_taxonomy_tag_explosion_prevention():
    existing_tags = [
        {"id": 20, "name": "python", "slug": "python"},
        {"id": 21, "name": "ai", "slug": "ai"},
        {"id": 22, "name": "fastapi", "slug": "fastapi"},
    ]
    # 8 proposed tags with duplicates and plurals
    proposed = ["python", "ai", "AI", "FastAPI", "models", "pipelines", "tools", "deployment"]
    resolved = TaxonomyResolver.resolve_tags(proposed, existing_tags, max_tags=2)
    assert len(resolved) <= 2
    assert resolved == [20, 21]


# ── 4. Media Planning & Rights Tests ─────────────────────────────────

def test_media_planner_creates_featured_image():
    plans = MediaPlanner.plan_article_media("Autonomous AI Engines", "AI Research")
    assert len(plans) >= 1
    assert plans[0].asset_type == AssetType.FEATURED_IMAGE
    assert plans[0].required is True
    assert plans[0].source_strategy == MediaSourceStrategy.AI_GENERATED


def test_media_rights_firewall():
    ok, _ = MediaRightsValidator.validate_rights("AI_GENERATED", "PROPRIETARY_AI", True)
    assert ok is True

    ok_cc0, _ = MediaRightsValidator.validate_rights("OFFICIAL_SOURCE", "CC0", True)
    assert ok_cc0 is True

    not_ok, msg = MediaRightsValidator.validate_rights("EXTERNAL", "NON_COMMERCIAL", False)
    assert not_ok is False
    assert "Non-commercial" in msg


def test_media_optimizer_hash_and_filename():
    data = b"image_bytes_123"
    h = MediaOptimizer.compute_hash(data)
    assert len(h) == 64
    fname = MediaOptimizer.generate_filename("Deep Research & Agents", "featured")
    assert fname.endswith(".webp")
    assert "deep-research-agents-featured" in fname



# ── 5. Internal Link Resolver Tests ──────────────────────────────────

def test_internal_link_candidate_resolution():
    candidates = [
        {
            "target_url": "https://example.com/ai-agents/",
            "target_slug": "ai-agents",
            "anchor_text": "autonomous AI agents",
            "source_section_id": "sec_1",
            "relevance_score": 0.95,
        },
        {
            "target_url": "https://example.com/self-slug/",
            "target_slug": "self-slug",
            "anchor_text": "self link",
            "source_section_id": "sec_2",
            "relevance_score": 0.5,
        },
    ]
    existing = [
        {"slug": "ai-agents", "url": "https://example.com/ai-agents/", "title": "Guide to AI Agents"},
    ]
    resolved = InternalLinkResolver.resolve_candidates(candidates, existing, current_article_slug="self-slug")
    assert len(resolved) == 1
    assert resolved[0].target_url == "https://example.com/ai-agents/"
    assert resolved[0].anchor_text == "autonomous AI agents"


def test_internal_link_injection_into_html():
    from app.schemas.publishing import ResolvedInternalLink

    links = [
        ResolvedInternalLink(
            source_section_id="sec_1",
            target_url="https://example.com/ai-agents/",
            target_title="AI Agents",
            anchor_text="autonomous AI agents",
            relevance_score=0.9,
        )
    ]
    html_text = "<p>We build autonomous AI agents that operate reliably.</p>"
    injected = InternalLinkResolver.inject_links_into_html(html_text, links)
    assert '<a href="https://example.com/ai-agents/">autonomous AI agents</a>' in injected


# ── 6. SEO Packaging & Schema Tests ──────────────────────────────────

def test_seo_packaging_and_slug_collision():
    slug = SEOPackager.clean_slug("Zohra AI: Modern Publishing Engine!")
    assert slug == "zohra-ai-modern-publishing-engine"

    existing_slugs = {"zohra-article", "zohra-article-2"}
    unique_slug = SEOPackager.resolve_slug_collision("zohra-article", existing_slugs)
    assert unique_slug == "zohra-article-3"

    pkg = SEOPackager.build_seo_package(
        title="Guide to AI Agents",
        meta_description="Learn how autonomous AI agents work.",
        base_url="https://example.com",
    )
    assert pkg.canonical_url == "https://example.com/guide-to-ai-agents/"
    assert pkg.robots_directive == "index,follow"


def test_schema_engine_article_and_faq():
    schema = SchemaEngine.generate_article_schema(
        title="AI Engineering Guide",
        canonical_url="https://example.com/ai-engineering-guide/",
        published_at_iso="2026-10-02T10:00:00Z",
        faqs=[{"question": "What is Zohra?", "answer": "An autonomous publishing engine."}],
    )
    graph = schema["@graph"]
    assert any(item["@type"] == "Article" for item in graph)
    assert any(item["@type"] == "FAQPage" for item in graph)


# ── 7. HTML Rendering & Sanitization Tests ───────────────────────────

def test_html_sanitizer_removes_scripts_and_handlers():
    dirty = '<p>Normal text <script>alert("hack")</script> <a href="javascript:steal()" onclick="doEvil()">click</a></p>'
    cleaned = PublicationRenderer.sanitize_html(dirty)
    assert "<script>" not in cleaned
    assert "alert" not in cleaned
    assert "onclick" not in cleaned
    assert "javascript:" not in cleaned


def test_renderer_outputs_structured_elements():
    rendered = PublicationRenderer.render_article(
        title="System Architecture",
        sections=[{"heading": "Core Engine", "body": "First paragraph.\n\nSecond paragraph."}],
        tables=[{"title": "Metrics", "headers": ["Model", "Score"], "rows": [["GPT-4", "98"]]}],
        faqs=[{"question": "Is it safe?", "answer": "Yes, verified."}],
    )
    assert "<h2>Core Engine</h2>" in rendered
    assert "<p>First paragraph.</p>" in rendered
    assert '<div class="zohra-table-wrap"><table>' in rendered
    assert "<h3>Metrics</h3>" in rendered
    assert '<div class="zohra-faq-item">' in rendered


# ── 8. Scheduling Engine & Timezone Tests ─────────────────────────────

def test_scheduler_timezone_conversion_and_dst():
    # 10:00 AM Kolkata (UTC+5:30) is 04:30 AM UTC
    kolkata_time = datetime(2026, 10, 2, 10, 0, 0)
    utc_time = PublicationScheduler.convert_local_to_utc(kolkata_time, "Asia/Kolkata")
    assert utc_time.hour == 4
    assert utc_time.minute == 30


def test_scheduler_publication_window_check():
    # Window 06:00-10:00 local time
    # 07:00 local is within window
    tz = "America/New_York"
    dt = datetime(2026, 10, 2, 7, 30, tzinfo=ZoneInfo(tz))
    utc_dt = dt.astimezone(UTC)
    assert PublicationScheduler.is_within_publication_window(utc_dt, tz, ["06:00-10:00"]) is True

    # 11:30 local is outside window
    dt_out = datetime(2026, 10, 2, 11, 30, tzinfo=ZoneInfo(tz))
    assert PublicationScheduler.is_within_publication_window(dt_out.astimezone(UTC), tz, ["06:00-10:00"]) is False


def test_scheduler_cadence_limits():
    # Exceeded daily limit
    with pytest.raises(SchedulingError, match="Daily publication limit reached"):
        PublicationScheduler.validate_cadence_limits(
            posts_published_today=5,
            max_posts_per_day=5,
            last_publish_time_utc=None,
            minimum_interval_minutes=60,
        )

    # Minimum interval violation
    now = datetime.now(UTC)
    last_pub = now - timedelta(minutes=20)
    with pytest.raises(SchedulingError, match="Minimum publication interval not elapsed"):
        PublicationScheduler.validate_cadence_limits(
            posts_published_today=1,
            max_posts_per_day=5,
            last_publish_time_utc=last_pub,
            minimum_interval_minutes=60,
        )


# ── 9. Post Verification Tests ───────────────────────────────────────

def test_post_verification_success():
    wp_data = {
        "id": 101,
        "status": "publish",
        "link": "https://example.com/my-post/",
        "title": {"rendered": "My Verified Article"},
        "content": {"rendered": "<p>" + "Long verified content " * 15 + "</p>"},
        "featured_media": 55,
    }
    res = PostVerifier.verify_post(
        wp_post_data=wp_data,
        expected_title="My Verified Article",
        expected_status="publish",
        expected_featured_media_id=55,
    )
    assert res["post_id"] == 101
    assert res["content_integrity"] == "PASS"


def test_post_verification_fails_on_truncated_body():
    wp_data = {
        "id": 102,
        "status": "publish",
        "link": "https://example.com/truncated/",
        "title": {"rendered": "Truncated"},
        "content": {"rendered": "<p>Too short</p>"},
    }
    with pytest.raises(VerificationError, match="content appears severely truncated"):
        PostVerifier.verify_post(wp_data, "Truncated", "publish", min_content_length=100)
