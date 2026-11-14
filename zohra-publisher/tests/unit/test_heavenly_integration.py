"""
Unit tests for Heavenly Insights Integration:
- Formatter (HTML stripping, blank-line separated paragraphs)
- Client security & token masking
- Header construction & Bearer authentication
- Draft creation & verification
- Production publishing
- Slug idempotency
- Error handling (Auth, RateLimit, Server, Client, Validation)
- PublishingPipeline integration
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.integrations.heavenly.client import HeavenlyClient
from app.integrations.heavenly.exceptions import (
    HeavenlyAuthError,
    HeavenlyRateLimitError,
    HeavenlyValidationError,
)
from app.integrations.heavenly.formatter import format_plain_text_body
from app.publishing.pipeline import PublishingPipeline
from app.schemas.publishing import PublicationMode


# ── Formatter Tests ───────────────────────────────────────────────────

def test_formatter_html_to_plain_text():
    html_input = (
        "<h1>How to Build a Daily Reading Habit</h1>"
        "<p>Reading every day is a transformative practice that shapes your thinking.</p>"
        "<p>Start by setting aside just <b>15 minutes</b> each morning with your coffee.</p>"
        "<div>Consistency matters more than speed.</div>"
    )
    result = format_plain_text_body(html_input)
    paragraphs = result.split("\n\n")

    assert len(paragraphs) == 4
    assert paragraphs[0] == "How to Build a Daily Reading Habit"
    assert "Reading every day is a transformative" in paragraphs[1]
    assert "15 minutes each morning" in paragraphs[2]
    assert "Consistency matters more than speed." in paragraphs[3]


def test_formatter_strips_scripts_and_styles():
    html_input = (
        "<style>body { font-size: 14px; }</style>"
        "<p>First paragraph.</p>"
        "<script>alert('xss');</script>"
        "<p>Second paragraph.</p>"
    )
    result = format_plain_text_body(html_input)
    assert "<script>" not in result
    assert "alert" not in result
    assert "<style>" not in result
    assert result == "First paragraph.\n\nSecond paragraph."


def test_formatter_handles_blank_lines_and_spaces():
    raw_text = "Paragraph one.\n\n\n\n\nParagraph two with &amp; entity."
    result = format_plain_text_body(raw_text)
    assert result == "Paragraph one.\n\nParagraph two with & entity."


# ── Client Security & Masking Tests ───────────────────────────────────

def test_client_repr_never_leaks_token():
    secret_token = "secret-super-confidential-token-12345"
    client = HeavenlyClient(
        site_url="https://heavenly-insights-educator.hamidansari1795.chatgpt.site",
        token=secret_token,
    )
    repr_str = repr(client)
    str_str = str(client)

    assert secret_token not in repr_str
    assert secret_token not in str_str
    assert "token_configured=True" in repr_str


def test_client_headers_contain_bearer_token():
    secret_token = "my-secret-bearer-token"
    client = HeavenlyClient(
        site_url="https://heavenly-insights-educator.hamidansari1795.chatgpt.site",
        token=secret_token,
    )
    headers = client._get_headers()
    assert headers["Authorization"] == f"Bearer {secret_token}"
    assert headers["Content-Type"] == "application/json"
    assert headers["Accept"] == "application/json"


def test_client_raises_if_token_is_missing_or_placeholder():
    client_empty = HeavenlyClient(token="")
    with pytest.raises(HeavenlyAuthError):
        client_empty._get_headers()

    client_placeholder = HeavenlyClient(token="PASTE_GENERATED_TOKEN_HERE")
    with pytest.raises(HeavenlyAuthError):
        client_placeholder._get_headers()


# ── Post Creation, Publishing & Idempotency ───────────────────────────

@pytest.mark.asyncio
async def test_create_draft_success():
    client = HeavenlyClient(
        site_url="https://heavenly-insights-educator.hamidansari1795.chatgpt.site",
        token="valid-test-token",
    )

    mock_response = httpx.Response(
        status_code=200,
        json={"id": 1, "status": "draft", "slug": "test-slug"},
        request=httpx.Request("POST", client.api_url),
    )

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_response

        res = await client.create_draft(
            title="How to Build a Daily Reading Habit",
            slug="how-to-build-a-daily-reading-habit",
            category="Books",
            excerpt="Practical steps to make reading part of your daily routine.",
            body="First paragraph.\n\nSecond paragraph.",
        )

        assert res["status"] == "draft"
        assert res["slug"] == "test-slug"

        # Verify sent payload
        call_kwargs = mock_req.call_args.kwargs
        sent_json = call_kwargs["json"]
        assert sent_json["title"] == "How to Build a Daily Reading Habit"
        assert sent_json["slug"] == "how-to-build-a-daily-reading-habit"
        assert sent_json["category"] == "Books"
        assert sent_json["status"] == "draft"
        assert sent_json["body"] == "First paragraph.\n\nSecond paragraph."


@pytest.mark.asyncio
async def test_publish_post_returns_url():
    client = HeavenlyClient(
        site_url="https://heavenly-insights-educator.hamidansari1795.chatgpt.site",
        token="valid-test-token",
    )

    expected_url = "https://heavenly-insights-educator.hamidansari1795.chatgpt.site/posts/test-slug"
    mock_response = httpx.Response(
        status_code=200,
        json={"id": 1, "status": "published", "slug": "test-slug", "url": expected_url},
        request=httpx.Request("POST", client.api_url),
    )

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_response

        res = await client.publish_post(
            title="How to Build a Daily Reading Habit",
            slug="how-to-build-a-daily-reading-habit",
            category="Books",
            excerpt="Practical steps to make reading part of your daily routine.",
            body="First paragraph.\n\nSecond paragraph.",
        )

        assert res["status"] == "published"
        assert res["url"] == expected_url

        call_kwargs = mock_req.call_args.kwargs
        assert call_kwargs["json"]["status"] == "published"


@pytest.mark.asyncio
async def test_same_slug_updates_article_idempotency():
    client = HeavenlyClient(
        site_url="https://heavenly-insights-educator.hamidansari1795.chatgpt.site",
        token="valid-test-token",
    )

    mock_response = httpx.Response(
        status_code=200,
        json={"id": 1, "status": "published", "slug": "consistent-slug", "updated": True},
        request=httpx.Request("POST", client.api_url),
    )

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_response

        # Call twice with same slug
        res1 = await client.create_or_update_post(
            title="First Version",
            slug="consistent-slug",
            category="Tech",
            excerpt="v1",
            body="v1 content",
            status="draft",
        )
        res2 = await client.create_or_update_post(
            title="Second Version",
            slug="consistent-slug",
            category="Tech",
            excerpt="v2",
            body="v2 content",
            status="published",
        )

        assert res1["slug"] == "consistent-slug"
        assert res2["slug"] == "consistent-slug"
        assert mock_req.call_count == 2
        # Check both calls sent the exact same slug
        first_call_slug = mock_req.call_args_list[0].kwargs["json"]["slug"]
        second_call_slug = mock_req.call_args_list[1].kwargs["json"]["slug"]
        assert first_call_slug == second_call_slug == "consistent-slug"


@pytest.mark.asyncio
async def test_list_posts():
    client = HeavenlyClient(
        site_url="https://heavenly-insights-educator.hamidansari1795.chatgpt.site",
        token="valid-test-token",
    )

    posts_data = [
        {"id": 1, "title": "Post 1", "status": "draft", "slug": "post-1"},
        {"id": 2, "title": "Post 2", "status": "published", "slug": "post-2"},
    ]
    mock_response = httpx.Response(
        status_code=200,
        json=posts_data,
        request=httpx.Request("GET", client.api_url),
    )

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_response
        res = await client.list_posts()
        assert res == posts_data


# ── Error Handling Tests ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_auth_error_raised():
    client = HeavenlyClient(token="invalid-token")
    mock_response = httpx.Response(
        status_code=401,
        text="Unauthorized",
        request=httpx.Request("POST", client.api_url),
    )

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_response
        with pytest.raises(HeavenlyAuthError):
            await client.create_draft("T", "s", "c", "e", "b")


@pytest.mark.asyncio
async def test_rate_limit_error_raised():
    client = HeavenlyClient(token="valid-token")
    mock_response = httpx.Response(
        status_code=429,
        text="Rate limited",
        request=httpx.Request("POST", client.api_url),
    )

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req, \
         patch("asyncio.sleep", new_callable=AsyncMock):
        mock_req.return_value = mock_response
        with pytest.raises(HeavenlyRateLimitError):
            await client.create_draft("T", "s", "c", "e", "b")


@pytest.mark.asyncio
async def test_validation_errors():
    client = HeavenlyClient(token="valid-token")

    with pytest.raises(HeavenlyValidationError, match="title cannot be empty"):
        await client.create_draft("", "slug", "cat", "exc", "body")

    with pytest.raises(HeavenlyValidationError, match="slug cannot be empty"):
        await client.create_draft("title", "", "cat", "exc", "body")

    with pytest.raises(HeavenlyValidationError, match="body cannot be empty"):
        await client.create_draft("title", "slug", "cat", "exc", "")

    with pytest.raises(HeavenlyValidationError, match="Invalid status"):
        await client.create_or_update_post("title", "slug", "cat", "exc", "body", status="pending")


# ── Pipeline Integration Test ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_publishing_pipeline_targets_heavenly():
    class MockHeavenlyClient(HeavenlyClient):
        def __init__(self):
            super().__init__(
                site_url="https://heavenly-insights-educator.hamidansari1795.chatgpt.site",
                token="test-mock-token",
            )
            self.saved_posts: list[dict[str, Any]] = []

        async def create_or_update_post(self, title, slug, category, excerpt, body, status="draft"):
            rec = {
                "id": len(self.saved_posts) + 1,
                "title": title,
                "slug": slug,
                "category": category,
                "excerpt": excerpt,
                "body": body,
                "status": status,
                "url": f"{self.site_url}/posts/{slug}" if status == "published" else None,
            }
            self.saved_posts.append(rec)
            return rec

    site_data = {
        "id": "site-test-1",
        "publisher_type": "heavenly",
        "publishing_enabled": True,
        "autonomous_publishing_enabled": False,
    }

    prepared_payload = {
        "title": "Building a Reading Habit",
        "slug": "building-a-reading-habit",
        "rendered_html": "<p>First paragraph.</p><p>Second paragraph.</p>",
        "payload_hash": "hash_12345",
        "publication_mode": PublicationMode.DRAFT,
        "seo_package": type("SEO", (), {
            "canonical_url": "https://heavenly-insights-educator.hamidansari1795.chatgpt.site/posts/building-a-reading-habit",
            "robots_directive": "index, follow",
            "meta_description": "A guide to reading habits.",
        })(),
    }

    draft_project_data = {
        "id": str(uuid.uuid4()),
        "primary_topic": "Books",
        "excerpt": "A guide to reading habits.",
        "citation_count": 0,
    }

    final_audit = {
        "audit_id": str(uuid.uuid4()),
        "content_hash": "chash_999",
        "audit_fingerprint": "af_888",
    }

    mock_client = MockHeavenlyClient()

    pkg = await PublishingPipeline.execute_publication(
        site_data=site_data,
        prepared_payload=prepared_payload,
        draft_project_data=draft_project_data,
        final_audit_package_data=final_audit,
        heavenly_client=mock_client,
    )

    assert pkg.publisher_target == "heavenly"
    assert pkg.heavenly is not None
    assert pkg.heavenly["status"] == "draft"
    assert pkg.heavenly["slug"] == "building-a-reading-habit"
    assert pkg.verification["target"] == "heavenly"
    assert pkg.verification["verified"] is True
