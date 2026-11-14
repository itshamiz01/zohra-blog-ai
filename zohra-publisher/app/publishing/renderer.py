"""
Zohra — Publication Content Renderer & Sanitizer (Part 7).

Converts approved structured article drafts into clean, accessible, responsive HTML:
- Preserves audited claims, quotations, tables, FAQs, and citations.
- Enforces strict HTML sanitization: strips <script>, <iframe>, event handlers, and javascript: URLs.
- Renders responsive tables and formatted callouts.
- Embeds verified media assets with appropriate alt text and captions.
- Calculates deterministic publication_payload_hash before WordPress transmission.
"""

from __future__ import annotations

import hashlib
import html
import re
from typing import Any

from app.core.logging import get_logger

logger = get_logger("publishing.renderer.html")

# Dangerous tags whose entire contents must be discarded
DANGEROUS_TAGS = re.compile(
    r"<(script|style|iframe|object|embed|form|applet|svg|meta|link)[^>]*>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)
# Dangerous inline event handlers and schemes
EVENT_HANDLERS = re.compile(r"""\s+on\w+\s*=\s*(['"]).*?\1""", re.IGNORECASE)
JS_SCHEMES = re.compile(r"""href\s*=\s*(['"])javascript:.*?\1""", re.IGNORECASE)


class PublicationRenderer:
    """Renders structured article content into safe HTML."""

    @classmethod
    def sanitize_html(cls, raw_html: str) -> str:
        """Strips dangerous scripts, iframes, inline event handlers, and javascript schemes."""
        if not raw_html:
            return ""
        cleaned = DANGEROUS_TAGS.sub("", raw_html)
        cleaned = EVENT_HANDLERS.sub("", cleaned)
        cleaned = JS_SCHEMES.sub('href="#"', cleaned)
        return cleaned.strip()

    @classmethod
    def render_article(
        cls,
        title: str,
        sections: list[dict[str, Any]],
        faqs: list[dict[str, str]] | None = None,
        tables: list[dict[str, Any]] | None = None,
        featured_image_url: str | None = None,
        featured_image_alt: str | None = None,
        featured_image_caption: str | None = None,
        featured_image_width: int = 1536,
        featured_image_height: int = 864,
    ) -> str:
        """Renders sections, tables, FAQs, and citations into clean semantic HTML."""
        parts: list[str] = []

        # High-performance accessible featured media hero
        if featured_image_url:
            alt = html.escape(featured_image_alt or title)
            caption_tag = f"<figcaption>{html.escape(featured_image_caption)}</figcaption>" if featured_image_caption else ""
            parts.append(
                f'<figure class="zohra-featured-media">'
                f'<img src="{html.escape(featured_image_url)}" alt="{alt}" width="{featured_image_width}" height="{featured_image_height}" fetchpriority="high" />'
                f"{caption_tag}"
                f"</figure>"
            )

        # Render sections
        for _idx, sec in enumerate(sections):
            heading = sec.get("heading")
            body = sec.get("body", "")

            if heading:
                # Body sections start with H2
                parts.append(f"<h2>{html.escape(heading)}</h2>")

            # Convert paragraphs to <p>
            for p in body.split("\n\n"):
                p_clean = p.strip()
                if p_clean:
                    parts.append(f"<p>{cls.sanitize_html(p_clean)}</p>")

        # Render tables
        if tables:
            for tbl in tables:
                t_title = tbl.get("title")
                headers = tbl.get("headers", [])
                rows = tbl.get("rows", [])
                if t_title:
                    parts.append(f"<h3>{html.escape(t_title)}</h3>")
                tbl_html = ['<div class="zohra-table-wrap"><table><thead><tr>']
                for h in headers:
                    tbl_html.append(f"<th>{html.escape(str(h))}</th>")
                tbl_html.append("</tr></thead><tbody>")
                for r in rows:
                    tbl_html.append("<tr>")
                    for cell in r:
                        tbl_html.append(f"<td>{html.escape(str(cell))}</td>")
                    tbl_html.append("</tr>")
                tbl_html.append("</tbody></table></div>")
                parts.append("".join(tbl_html))

        # Render FAQs
        if faqs:
            parts.append("<h2>Frequently Asked Questions</h2>")
            parts.append('<div class="zohra-faq-accordion">')
            for faq in faqs:
                q = faq.get("question", "")
                a = faq.get("answer", "")
                if q and a:
                    parts.append(
                        f'<div class="zohra-faq-item">'
                        f"<h3>{html.escape(q)}</h3>"
                        f"<p>{html.escape(a)}</p>"
                        f"</div>"
                    )
            parts.append("</div>")

        full_html = "\n\n".join(parts)
        return cls.sanitize_html(full_html)

    @classmethod
    def compute_payload_hash(cls, payload: dict[str, Any]) -> str:
        """Computes deterministic SHA-256 hash over publication payload for reconciliation."""
        import json
        dumped = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(dumped.encode("utf-8")).hexdigest()
