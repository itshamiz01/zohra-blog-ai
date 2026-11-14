"""
Zohra — Controlled Research Fetcher & Document Normalizer.

Securely acquires external documents with SSRF validation, circuit breaker protection,
content sanitization, and change detection / version tracking.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.core.logging import get_logger
from app.discovery.security.circuit_breaker import CircuitBreaker
from app.discovery.security.sanitizer import ContentSanitizer
from app.discovery.security.ssrf import SSRFValidator

logger = get_logger("research.fetcher")


class FetchedDocument:
    def __init__(
        self,
        url: str,
        canonical_url: str,
        http_status: int,
        title: str | None,
        author: str | None,
        published_at: datetime | None,
        normalized_text: str,
        content_hash: str,
        has_changed: bool = False,
        change_summary: str | None = None,
        headers: dict[str, str] | None = None,
    ):
        self.url = url
        self.canonical_url = canonical_url
        self.http_status = http_status
        self.title = title
        self.author = author
        self.published_at = published_at
        self.normalized_text = normalized_text
        self.content_hash = content_hash
        self.has_changed = has_changed
        self.change_summary = change_summary
        self.headers = headers or {}


class ControlledResearchFetcher:
    """Secure, resilient fetcher for research documents with versioning & change detection."""

    MAX_BYTES = 5 * 1024 * 1024  # 5 MB
    TIMEOUT_SECONDS = 10.0

    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}

    def _get_breaker(self, domain: str) -> CircuitBreaker:
        if domain not in self._breakers:
            self._breakers[domain] = CircuitBreaker(failure_threshold=4, cooldown_seconds=30.0)
        return self._breakers[domain]

    async def fetch_document(
        self,
        url: str,
        previous_content_hash: str | None = None,
    ) -> FetchedDocument:
        """Fetches and normalizes a webpage or JSON document safely."""
        # 1. SSRF and Protocol Validation
        is_safe, error_msg = SSRFValidator.validate_url(url)
        if not is_safe:
            raise ValueError(f"SSRF validation blocked URL {url}: {error_msg}")

        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # 2. Circuit Breaker check
        breaker = self._get_breaker(domain)
        if not breaker.can_execute():
            raise ConnectionError(f"Circuit breaker OPEN for domain {domain}")

        # 3. HTTP Fetch with size limit
        headers = {
            "User-Agent": "ZohraResearchBot/1.0 (+https://zohrablog.com/bot; research@zohrablog.com)",
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        }

        try:
            async with httpx.AsyncClient(
                timeout=self.TIMEOUT_SECONDS,
                follow_redirects=True,
                max_redirects=3,
            ) as client:
                resp = await client.get(url, headers=headers)
                breaker.record_success()
        except Exception as exc:
            breaker.record_failure()
            logger.warning("research_fetch_failed: url=%s, error=%s", url, str(exc))
            raise

        content_bytes = resp.content
        if len(content_bytes) > self.MAX_BYTES:
            content_bytes = content_bytes[: self.MAX_BYTES]

        content_type = resp.headers.get("content-type", "").lower()
        encoding = resp.encoding or "utf-8"

        try:
            raw_text = content_bytes.decode(encoding, errors="replace")
        except (LookupError, UnicodeDecodeError):
            raw_text = content_bytes.decode("utf-8", errors="replace")

        # 4. Content Extraction & Normalization
        title: str | None = None
        author: str | None = None
        published_at: datetime | None = None
        normalized_body: str = ""

        if "json" in content_type:
            # API response
            normalized_body = ContentSanitizer.sanitize_text(raw_text)
        else:
            # HTML extraction
            soup = BeautifulSoup(raw_text, "html.parser")

            # Extract title
            title_tag = soup.find("title")
            if title_tag:
                title = title_tag.get_text(strip=True)

            # Extract meta tags
            author_meta = (
                soup.find("meta", attrs={"name": "author"})
                or soup.find("meta", attrs={"property": "article:author"})
            )
            if author_meta and author_meta.get("content"):
                author = author_meta["content"].strip()

            date_meta = (
                soup.find("meta", attrs={"property": "article:published_time"})
                or soup.find("meta", attrs={"name": "publication_date"})
                or soup.find("meta", attrs={"name": "date"})
            )
            if date_meta and date_meta.get("content"):
                try:
                    dt_str = date_meta["content"].strip()
                    # Strip trailing Z or parse standard ISO format
                    dt_clean = re.sub(r"Z$", "+00:00", dt_str)
                    published_at = datetime.fromisoformat(dt_clean)
                except (ValueError, TypeError):
                    pass

            # Strip noisy HTML elements
            for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "aside", "svg"]):
                tag.decompose()

            # Find main article container or fall back to body
            main_elem = (
                soup.find("article")
                or soup.find("main")
                or soup.find("div", class_=re.compile(r"content|post-body|entry-content", re.I))
                or soup.find("body")
            )

            if main_elem:
                text_content = main_elem.get_text(separator="\n", strip=True)
            else:
                text_content = soup.get_text(separator="\n", strip=True)

            # Sanitize content against XSS / invisible characters / control tokens
            normalized_body = ContentSanitizer.sanitize_text(text_content)

        # 5. Compute content hash
        content_hash = hashlib.sha256(normalized_body.encode("utf-8")).hexdigest()

        # 6. Change detection
        has_changed = False
        change_summary = None
        if previous_content_hash and previous_content_hash != content_hash:
            has_changed = True
            change_summary = f"Content hash updated from {previous_content_hash[:8]} to {content_hash[:8]}"

        canonical_url = str(resp.url)

        return FetchedDocument(
            url=url,
            canonical_url=canonical_url,
            http_status=resp.status_code,
            title=title,
            author=author,
            published_at=published_at,
            normalized_text=normalized_body,
            content_hash=content_hash,
            has_changed=has_changed,
            change_summary=change_summary,
            headers=dict(resp.headers),
        )
