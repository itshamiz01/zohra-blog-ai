"""
Regression tests for the article cover-image guarantee.

These lock in the fix for "sometimes the article is published without an image".

Two independent defects used to cause that:
  1. The Heavenly Insights post schema exposes ``cover_image_url`` /
     ``cover_image_alt``. Zohra sent ``image_url`` and ``featured_image``,
     which the API silently discarded.
  2. The value sent was a relative app path ("/storage/media/articles/x.webp")
     that resolves to nothing on the live blog. Covers must be uploaded to
     ``POST /api/images`` and referenced by the returned public absolute URL.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.exceptions import ZohraError
from app.integrations.heavenly.client import (
    HeavenlyClient,
    is_public_absolute_url,
)
from app.integrations.heavenly.exceptions import HeavenlyImageUploadError

SITE = "https://heavenly-insights-educator.hamidansari1795.chatgpt.site"
PUBLIC_COVER = f"{SITE}/api/images/11111111-2222-3333-4444-555555555555"


def _client() -> HeavenlyClient:
    return HeavenlyClient(site_url=SITE, token="valid-test-token")


# ── is_public_absolute_url ────────────────────────────────────────────


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (PUBLIC_COVER, True),
        ("https://cdn.example.com/covers/a.webp", True),
        ("http://cdn.example.com/covers/a.webp", True),
        # The exact shape the old code produced -> unusable on a live blog.
        ("/storage/media/articles/a.webp", False),
        ("storage/media/articles/a.webp", False),
        ("", False),
        (None, False),
        ("http://localhost:8000/storage/a.webp", False),
        ("http://127.0.0.1:8000/storage/a.webp", False),
        ("../covers/a.webp", False),
    ],
)
def test_is_public_absolute_url(url, expected):
    assert is_public_absolute_url(url) is expected


# ── Post payload uses the fields the API actually reads ───────────────


@pytest.mark.asyncio
async def test_post_payload_uses_cover_image_url_not_legacy_keys():
    client = _client()
    mock_response = httpx.Response(
        status_code=200,
        json={"id": "1", "status": "published", "slug": "s", "url": f"{SITE}/articles/s"},
        request=httpx.Request("POST", client.api_url),
    )

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_response

        await client.create_or_update_post(
            title="A Title",
            slug="a-title",
            category="Technology",
            excerpt="Excerpt",
            body="Paragraph one.\n\nParagraph two.",
            status="published",
            image_url=PUBLIC_COVER,
            cover_image_alt="A descriptive alt text",
        )

        sent = mock_req.call_args.kwargs["json"]
        assert sent["cover_image_url"] == PUBLIC_COVER
        assert sent["cover_image_alt"] == "A descriptive alt text"
        # The API ignores these; sending them caused silent cover loss.
        assert "image_url" not in sent
        assert "featured_image" not in sent


@pytest.mark.asyncio
async def test_post_payload_omits_cover_when_no_image():
    client = _client()
    mock_response = httpx.Response(
        status_code=200,
        json={"id": "1", "status": "draft", "slug": "s"},
        request=httpx.Request("POST", client.api_url),
    )

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_response
        await client.create_or_update_post(
            title="A Title",
            slug="a-title",
            category="Technology",
            excerpt="Excerpt",
            body="Body text.",
            status="draft",
        )
        sent = mock_req.call_args.kwargs["json"]
        assert "cover_image_url" not in sent


@pytest.mark.asyncio
async def test_publish_post_forwards_cover_alt():
    client = _client()
    mock_response = httpx.Response(
        status_code=200,
        json={"id": "1", "status": "published", "slug": "s", "url": f"{SITE}/articles/s"},
        request=httpx.Request("POST", client.api_url),
    )

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_response
        await client.publish_post(
            title="T",
            slug="s",
            category="C",
            excerpt="E",
            body="B",
            image_url=PUBLIC_COVER,
            cover_image_alt="Alt",
        )
        sent = mock_req.call_args.kwargs["json"]
        assert sent["cover_image_url"] == PUBLIC_COVER
        assert sent["cover_image_alt"] == "Alt"


# ── Upload endpoint contract ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_upload_image_posts_multipart_file_field_and_returns_url():
    client = _client()
    uploaded = {
        "id": "11111111-2222-3333-4444-555555555555",
        "url": PUBLIC_COVER,
        "mime": "image/webp",
        "size": 1234,
    }
    mock_response = httpx.Response(
        status_code=201,
        json=uploaded,
        request=httpx.Request("POST", client.images_url),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        result = await client.upload_image(b"RIFFxxxxWEBP", filename="cover.webp")

        assert result["url"] == PUBLIC_COVER
        kwargs = mock_post.call_args.kwargs
        assert mock_post.call_args.args[0] == client.images_url
        # The endpoint rejects anything that is not a "file" multipart field.
        assert "file" in kwargs["files"]
        name, payload, mime = kwargs["files"]["file"]
        assert name == "cover.webp"
        assert payload == b"RIFFxxxxWEBP"
        assert mime == "image/webp"


@pytest.mark.asyncio
async def test_upload_image_raises_on_client_error():
    client = _client()
    mock_response = httpx.Response(
        status_code=400,
        json={"error": "Send multipart/form-data with an image file field."},
        request=httpx.Request("POST", client.images_url),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        with pytest.raises(HeavenlyImageUploadError):
            await client.upload_image(b"data")


@pytest.mark.asyncio
async def test_upload_image_raises_on_empty_bytes():
    client = _client()
    with pytest.raises(HeavenlyImageUploadError):
        await client.upload_image(b"")


@pytest.mark.asyncio
async def test_upload_image_raises_when_url_missing_in_response():
    client = _client()
    mock_response = httpx.Response(
        status_code=201,
        json={"id": "abc"},
        request=httpx.Request("POST", client.images_url),
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        with pytest.raises(HeavenlyImageUploadError):
            await client.upload_image(b"data")


# ── ensure_public_cover_url ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_ensure_public_cover_url_uploads_relative_storage_path():
    """The old bug: a relative /storage path was published as-is -> broken image."""
    client = _client()
    mock_response = httpx.Response(
        status_code=201,
        json={"id": "1", "url": PUBLIC_COVER},
        request=httpx.Request("POST", client.images_url),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        resolved = await client.ensure_public_cover_url(
            image_bytes=b"RIFFxxxxWEBP",
            candidate_url="/storage/media/articles/cover.webp",
            filename="cover.webp",
        )

        assert resolved == PUBLIC_COVER
        assert mock_post.call_count == 1


@pytest.mark.asyncio
async def test_ensure_public_cover_url_keeps_existing_absolute_url():
    client = _client()
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        resolved = await client.ensure_public_cover_url(candidate_url=PUBLIC_COVER)
        assert resolved == PUBLIC_COVER
        assert mock_post.call_count == 0


@pytest.mark.asyncio
async def test_ensure_public_cover_url_returns_none_without_bytes_or_url():
    client = _client()
    resolved = await client.ensure_public_cover_url(candidate_url="/storage/x.webp")
    assert resolved is None


# ── Post-publish public verification ─────────────────────────────────


@pytest.mark.asyncio
async def test_verify_cover_image_public_succeeds_on_200():
    client = _client()
    mock_response = httpx.Response(
        status_code=200,
        content=b"RIFFxxxxWEBP",
        request=httpx.Request("GET", PUBLIC_COVER),
    )
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        assert await client.verify_cover_image_public(PUBLIC_COVER) is True


@pytest.mark.asyncio
async def test_verify_cover_image_public_retries_then_fails_on_404():
    """
    Draft/orphan images 404 on the publisher until a published post references
    them, so verification must retry and report False rather than raise.
    """
    client = _client()
    mock_response = httpx.Response(
        status_code=404,
        content=b"Not found",
        request=httpx.Request("GET", PUBLIC_COVER),
    )
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        ok = await client.verify_cover_image_public(PUBLIC_COVER, attempts=2, delay_seconds=0.01)
        assert ok is False
        assert mock_get.call_count == 2


@pytest.mark.asyncio
async def test_verify_cover_image_public_rejects_non_public_url():
    client = _client()
    assert await client.verify_cover_image_public("/storage/media/articles/x.webp") is False
    assert await client.verify_cover_image_public(None) is False


# ── "Every article gets an image" guarantee ──────────────────────────


class _AlwaysFailingProvider:
    name = "broken"
    is_generative_ai = True

    async def generate_image(self, prompt):  # noqa: ANN001, ARG002
        raise RuntimeError("provider exploded")


class _Router:
    def __init__(self, provider):  # noqa: ANN001
        self._provider = provider

    def get_provider(self, name=None):  # noqa: ANN001, ARG002
        return self._provider


@pytest.mark.asyncio
async def test_generation_failure_still_yields_image_bytes():
    """
    With ARTICLE_IMAGE_GUARANTEE_IMAGE (default True) a total provider outage must
    still produce usable cover bytes, so no article is ever published imageless.
    """
    from app.publishing.media import ImageProvider

    fake_settings = MagicMock()
    fake_settings.ARTICLE_IMAGE_MAX_REGENERATIONS = 0
    fake_settings.ARTICLE_IMAGE_ALLOW_PROCEDURAL_FALLBACK = False
    fake_settings.ARTICLE_IMAGE_REQUIRE_GENERATIVE_AI = True
    fake_settings.ARTICLE_IMAGE_GUARANTEE_IMAGE = True
    fake_settings.STORAGE_DIR = "./storage"
    fake_settings.ARTICLE_IMAGE_RELEVANCE_MIN_SCORE = 0.0

    with (
        patch("app.core.config.get_settings", return_value=fake_settings),
        patch(
            "app.media.providers.router.get_image_provider_router",
            return_value=_Router(_AlwaysFailingProvider()),
        ),
    ):
        res = await ImageProvider.generate_article_featured_image(
            title="Why Every Article Needs A Cover",
            topic="Publishing",
            category="Technology",
            full_text="Body text about publishing reliably.",
        )

    assert res["bytes"], "generation must always yield bytes under the guarantee"
    assert len(res["bytes"]) > 0
    assert res["filename"]
    # Marked as a non-generative fallback so governance can still see the degrade.
    assert res["source_type"] in ("PROCEDURAL", "AI_GENERATED")


@pytest.mark.asyncio
async def test_generation_failure_without_guarantee_returns_no_bytes():
    """Opting out of the guarantee restores the old (blocking) behaviour."""
    from app.publishing.media import ImageProvider

    fake_settings = MagicMock()
    fake_settings.ARTICLE_IMAGE_MAX_REGENERATIONS = 0
    fake_settings.ARTICLE_IMAGE_ALLOW_PROCEDURAL_FALLBACK = False
    fake_settings.ARTICLE_IMAGE_REQUIRE_GENERATIVE_AI = True
    fake_settings.ARTICLE_IMAGE_GUARANTEE_IMAGE = False
    fake_settings.STORAGE_DIR = "./storage"

    with (
        patch("app.core.config.get_settings", return_value=fake_settings),
        patch(
            "app.media.providers.router.get_image_provider_router",
            return_value=_Router(_AlwaysFailingProvider()),
        ),
    ):
        res = await ImageProvider.generate_article_featured_image(
            title="No Cover Allowed",
            topic="Publishing",
            category="Technology",
        )

    assert res["bytes"] is None
    assert res["public_url"] is None
    # Result shape stays stable for callers.
    assert res["status"] == "FAILED"


# ── Publisher refuses imageless publication ───────────────────────────


@pytest.mark.asyncio
async def test_heavenly_publisher_blocks_when_no_public_image():
    from app.publishing.publishers.heavenly import HeavenlyPublisher
    from app.schemas.publishing import PublicationMode

    publisher = HeavenlyPublisher(heavenly_client=MagicMock())
    prepared = {
        "title": "T",
        "slug": "s",
        "rendered_html": "<p>Body</p>",
        "featured_image_url": "/storage/media/articles/s.webp",
        "featured_image_bytes": None,
        "featured_image_alt": "Alt",
        "publication_mode": PublicationMode.PUBLISH_NOW,
        "seo_package": None,
    }

    fake_settings = MagicMock()
    fake_settings.ARTICLE_FEATURED_IMAGE_REQUIRED = True
    fake_settings.HEAVENLY_UPLOAD_IMAGES = True

    with patch("app.publishing.publishers.heavenly.get_settings", return_value=fake_settings):
        with pytest.raises(ZohraError) as exc:
            await publisher.publish_article(prepared_payload=prepared, site_data={})

    assert exc.value.code == "MEDIA_BLOCKED"


@pytest.mark.asyncio
async def test_heavenly_publisher_uploads_bytes_then_publishes_public_url():
    from app.publishing.publishers.heavenly import HeavenlyPublisher
    from app.schemas.publishing import PublicationMode

    mock_client = MagicMock()
    mock_client.ensure_public_cover_url = AsyncMock(return_value=PUBLIC_COVER)
    mock_client.create_or_update_post = AsyncMock(
        return_value={"status": "published", "url": f"{SITE}/articles/s"}
    )
    mock_client.site_url = SITE

    publisher = HeavenlyPublisher(heavenly_client=mock_client)
    prepared = {
        "title": "T",
        "slug": "s",
        "rendered_html": "<p>Body</p>",
        "featured_image_url": "/storage/media/articles/s.webp",
        "featured_image_bytes": b"RIFFxxxxWEBP",
        "featured_image_filename": "s.webp",
        "featured_image_alt": "Alt text",
        "publication_mode": PublicationMode.PUBLISH_NOW,
        "seo_package": None,
    }

    fake_settings = MagicMock()
    fake_settings.ARTICLE_FEATURED_IMAGE_REQUIRED = True
    fake_settings.HEAVENLY_UPLOAD_IMAGES = True

    with patch("app.publishing.publishers.heavenly.get_settings", return_value=fake_settings):
        result = await publisher.publish_article(prepared_payload=prepared, site_data={})

    mock_client.ensure_public_cover_url.assert_awaited_once()
    assert mock_client.create_or_update_post.await_args.kwargs["image_url"] == PUBLIC_COVER
    assert mock_client.create_or_update_post.await_args.kwargs["cover_image_alt"] == "Alt text"
    assert result["featured_image"] == PUBLIC_COVER
