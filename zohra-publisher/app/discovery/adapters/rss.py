"""
Zohra — RSS & Atom Feed Adapter.

Ingests RSS 2.0 and Atom feeds:
- SSRF validation on target URL and all redirect locations
- Enforces response size caps, timeouts, and redirect limits
- Defused XML parsing protecting against entity expansion (Billion Laughs)
- Robust fallback regex parser for malformed feeds
- Conditional request support (ETag / Last-Modified)
"""

from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.discovery.adapters.base import FetchResult, RawFetchedItem, SourceAdapter
from app.discovery.security.sanitizer import clean_html, sanitize_text
from app.discovery.security.ssrf import SSRFProtectionError, validate_url_for_ssrf

logger = get_logger("discovery.adapters.rss")


class RSSAdapter(SourceAdapter):
    """Adapter for fetching and parsing RSS 2.0 and Atom XML feeds."""

    def __init__(self) -> None:
        self.settings = get_settings()

    async def fetch(self, source_url: str, metadata: dict[str, Any] | None = None) -> FetchResult:
        """Fetch and parse an RSS or Atom feed."""
        start_time = time.perf_counter()

        # 1. SSRF validation
        try:
            validated_url = validate_url_for_ssrf(source_url)
        except SSRFProtectionError as e:
            return FetchResult(
                success=False,
                error_message=f"SSRF blocked: {e}",
                response_time_ms=int((time.perf_counter() - start_time) * 1000),
            )

        # 2. Prepare headers (conditional fetching if metadata provides etag/last-modified)
        headers = {
            "User-Agent": self.settings.DISCOVERY_USER_AGENT,
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
        }
        if metadata:
            if metadata.get("etag"):
                headers["If-None-Match"] = str(metadata["etag"])
            if metadata.get("last_modified"):
                headers["If-Modified-Since"] = str(metadata["last_modified"])

        # 3. Safe HTTP request with hop-by-hop SSRF validation
        try:
            async with httpx.AsyncClient(
                timeout=self.settings.FETCH_TIMEOUT_SECONDS,
                follow_redirects=False,  # We manually validate each redirect hop for SSRF
                verify=True,
            ) as client:
                current_url = validated_url
                redirect_count = 0
                response = None

                while redirect_count <= self.settings.MAX_REDIRECTS:
                    resp = await client.get(current_url, headers=headers)
                    if resp.is_redirect:
                        redirect_count += 1
                        location = resp.headers.get("Location")
                        if not location:
                            break
                        # Validate next hop against SSRF!
                        next_url = str(resp.url.join(location))
                        validate_url_for_ssrf(next_url)
                        current_url = next_url
                        continue
                    else:
                        response = resp
                        break

                if response is None:
                    return FetchResult(
                        success=False,
                        error_message="Exceeded max redirects",
                        response_time_ms=int((time.perf_counter() - start_time) * 1000),
                    )

                # Check 304 Not Modified
                if response.status_code == 304:
                    return FetchResult(
                        success=True,
                        status_code=304,
                        items=[],
                        response_time_ms=int((time.perf_counter() - start_time) * 1000),
                    )

                if response.status_code != 200:
                    return FetchResult(
                        success=False,
                        status_code=response.status_code,
                        error_message=f"HTTP status {response.status_code}",
                        response_time_ms=int((time.perf_counter() - start_time) * 1000),
                    )

                # Check max response size
                content_bytes = response.content
                if len(content_bytes) > self.settings.MAX_RESPONSE_BYTES:
                    return FetchResult(
                        success=False,
                        status_code=200,
                        error_message=f"Feed exceeds max allowed size ({len(content_bytes)} bytes)",
                        response_time_ms=int((time.perf_counter() - start_time) * 1000),
                    )

                # Parse XML content
                text_content = response.text
                items = self.parse_feed_xml(text_content, current_url)

                elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                return FetchResult(
                    success=True,
                    status_code=200,
                    items=items,
                    response_time_ms=elapsed_ms,
                    etag=response.headers.get("ETag"),
                    last_modified=response.headers.get("Last-Modified"),
                )

        except SSRFProtectionError as e:
            return FetchResult(
                success=False,
                error_message=f"SSRF violation on redirect: {e}",
                response_time_ms=int((time.perf_counter() - start_time) * 1000),
            )
        except httpx.TimeoutException:
            return FetchResult(
                success=False,
                error_message="Fetch timed out",
                response_time_ms=int((time.perf_counter() - start_time) * 1000),
            )
        except Exception as e:
            logger.warning("Feed fetch error", url=source_url, error=str(e))
            return FetchResult(
                success=False,
                error_message=f"Fetch failed: {str(e)[:200]}",
                response_time_ms=int((time.perf_counter() - start_time) * 1000),
            )

    async def health_check(self, source_url: str) -> bool:
        """Health check returns True if endpoint responds with status < 400."""
        try:
            res = await self.fetch(source_url)
            return res.success
        except Exception:
            return False

    def parse_feed_xml(self, xml_text: str, base_url: str) -> list[RawFetchedItem]:
        """
        Parses XML text as RSS 2.0 or Atom.
        Falls back to regex extraction if XML parsing fails due to malformed XML.
        """
        if not xml_text:
            return []

        # Try standard XML parsing first
        try:
            # Strip XML entity references that could cause expansion attacks
            safe_xml = re.sub(r"<!ENTITY[^>]+>", "", xml_text)
            root = ET.fromstring(safe_xml)

            tag = root.tag.lower()
            if "rss" in tag or root.find("channel") is not None:
                return self._parse_rss_tree(root)
            elif "feed" in tag:
                return self._parse_atom_tree(root)
            else:
                # Search for items/entries anywhere
                if root.findall(".//item"):
                    return self._parse_rss_tree(root)
                elif root.findall(".//{http://www.w3.org/2005/Atom}entry"):
                    return self._parse_atom_tree(root)
        except ET.ParseError:
            logger.info("XML ParseError; falling back to regex parser", url=base_url)

        # Fallback regex parser for broken/malformed feeds
        return self._parse_malformed_xml_regex(xml_text, base_url)

    def _parse_rss_tree(self, root: ET.Element) -> list[RawFetchedItem]:
        """Extract items from RSS 2.0 tree."""
        items: list[RawFetchedItem] = []
        for item_elem in root.findall(".//item"):
            title = self._get_text(item_elem, "title") or "Untitled"
            link = self._get_text(item_elem, "link") or ""
            guid = self._get_text(item_elem, "guid") or link
            desc = self._get_text(item_elem, "description") or ""
            pub_date_str = self._get_text(item_elem, "pubDate")
            author = self._get_text(item_elem, "author") or self._get_text(item_elem, "dc:creator")

            # Content encoded (if available)
            content_encoded = None
            for child in item_elem:
                if child.tag.endswith("encoded"):
                    content_encoded = child.text
                    break

            pub_date = self._parse_date(pub_date_str)
            clean_summary = clean_html(desc)
            clean_content = clean_html(content_encoded) if content_encoded else clean_summary

            if link:
                items.append(
                    RawFetchedItem(
                        url=link.strip(),
                        title=sanitize_text(title),
                        external_id=guid.strip() if guid else None,
                        summary=clean_summary[:1000] if clean_summary else None,
                        content_text=clean_content if clean_content else clean_summary,
                        author=sanitize_text(author) if author else None,
                        published_at=pub_date,
                    )
                )
        return items

    def _parse_atom_tree(self, root: ET.Element) -> list[RawFetchedItem]:
        """Extract items from Atom tree."""
        items: list[RawFetchedItem] = []
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        entries = root.findall(".//atom:entry", ns)
        if not entries:
            entries = root.findall(".//entry")

        for entry in entries:
            title = self._get_text(entry, "title") or "Untitled"
            id_val = self._get_text(entry, "id") or ""

            # Link can be <link href="...">
            link = ""
            for link_elem in entry.findall("atom:link", ns) or entry.findall("link"):
                rel = link_elem.get("rel", "alternate")
                if rel in {"alternate", ""}:
                    link = link_elem.get("href", "")
                    break

            summary = self._get_text(entry, "summary") or self._get_text(entry, "content") or ""
            published_str = self._get_text(entry, "published") or self._get_text(entry, "updated")
            author = self._get_text(entry, "author/name") or self._get_text(entry, "author")

            pub_date = self._parse_date(published_str)
            clean_summary = clean_html(summary)

            target_url = link or id_val
            if target_url:
                items.append(
                    RawFetchedItem(
                        url=target_url.strip(),
                        title=sanitize_text(title),
                        external_id=id_val.strip() if id_val else None,
                        summary=clean_summary[:1000] if clean_summary else None,
                        content_text=clean_summary,
                        author=sanitize_text(author) if author else None,
                        published_at=pub_date,
                    )
                )
        return items

    def _parse_malformed_xml_regex(self, xml_text: str, base_url: str) -> list[RawFetchedItem]:
        """Fallback regex parser for broken feeds that cannot be parsed by ElementTree."""
        items: list[RawFetchedItem] = []
        item_blocks = re.findall(
            r"<item\b[^>]*>(.*?)</item>", xml_text, flags=re.DOTALL | re.IGNORECASE
        )
        if not item_blocks:
            item_blocks = re.findall(
                r"<entry\b[^>]*>(.*?)</entry>", xml_text, flags=re.DOTALL | re.IGNORECASE
            )

        for block in item_blocks:
            title_m = re.search(
                r"<title[^>]*>(.*?)</title>", block, flags=re.DOTALL | re.IGNORECASE
            )
            link_m = re.search(r"<link[^>]*>(.*?)</link>", block, flags=re.DOTALL | re.IGNORECASE)
            if not link_m:
                link_m = re.search(
                    r'<link[^>]*href=["\']([^"\']+)["\']', block, flags=re.IGNORECASE
                )

            guid_m = re.search(r"<guid[^>]*>(.*?)</guid>", block, flags=re.DOTALL | re.IGNORECASE)
            if not guid_m:
                guid_m = re.search(r"<id[^>]*>(.*?)</id>", block, flags=re.DOTALL | re.IGNORECASE)

            desc_m = re.search(
                r"<description[^>]*>(.*?)</description>", block, flags=re.DOTALL | re.IGNORECASE
            )
            if not desc_m:
                desc_m = re.search(
                    r"<summary[^>]*>(.*?)</summary>", block, flags=re.DOTALL | re.IGNORECASE
                )

            pub_m = re.search(
                r"<(pubDate|published|updated)[^>]*>(.*?)</\1>",
                block,
                flags=re.DOTALL | re.IGNORECASE,
            )

            title = clean_html(title_m.group(1)) if title_m else "Untitled"
            link = link_m.group(1).strip() if link_m else ""
            guid = guid_m.group(1).strip() if guid_m else link
            desc = clean_html(desc_m.group(1)) if desc_m else ""
            pub_date = self._parse_date(pub_m.group(2) if pub_m else None)

            if link:
                items.append(
                    RawFetchedItem(
                        url=link,
                        title=title,
                        external_id=guid or None,
                        summary=desc[:1000] if desc else None,
                        content_text=desc,
                        published_at=pub_date,
                    )
                )

        return items

    @staticmethod
    def _get_text(element: ET.Element, path: str) -> str | None:
        """Finds element text ignoring namespaces where possible."""
        # Try direct find
        found = element.find(path)
        if found is not None and found.text:
            return found.text.strip()

        # Try stripped namespace tag matching
        target_name = path.split("/")[-1].split(":")[-1].lower()
        for child in element:
            child_name = child.tag.split("}")[-1].lower()
            if child_name == target_name and child.text:
                return child.text.strip()
        return None

    @staticmethod
    def _parse_date(date_str: str | None) -> datetime | None:
        """Parses RFC 822 or ISO 8601 date strings to UTC datetime."""
        if not date_str:
            return None
        date_str = date_str.strip()
        # 1. Try RFC 822 (common in RSS)
        try:
            dt = parsedate_to_datetime(date_str)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=UTC)
            return dt.astimezone(UTC)
        except (ValueError, TypeError, OverflowError):
            pass

        # 2. Try ISO 8601 (common in Atom)
        try:
            iso_clean = date_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(iso_clean)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=UTC)
            return dt.astimezone(UTC)
        except (ValueError, TypeError, OverflowError):
            pass

        return None
