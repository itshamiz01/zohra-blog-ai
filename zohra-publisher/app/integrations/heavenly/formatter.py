"""
Zohra — Heavenly Insights Content Formatter.

Formats article body into clean plain text with blank lines (\n\n) between paragraphs,
as required by the Heavenly Insights API specification.
"""

from __future__ import annotations

import html
import re


def format_plain_text_body(content: str) -> str:
    """
    Converts HTML or markdown content into clean plain text suitable for Heavenly Insights.

    Rules:
    - Strips all HTML tags and converts block elements to double newlines.
    - Strips scripts and style tags.
    - Resolves HTML entities (e.g., &nbsp;, &amp;).
    - Preserves logical paragraphs separated by blank lines (\n\n).
    - Cleans up excessive whitespace.
    """
    if not content:
        return ""

    text = content.strip()

    # 1. Remove script and style elements completely
    text = re.sub(r"<(script|style)[^>]*>[\s\S]*?</\1>", "", text, flags=re.IGNORECASE)

    # 2. Replace block breaks with newlines
    # Headings, paragraphs, div, blockquote, hr, br, li
    text = re.sub(r"<\s*br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<\s*/?(h[1-6]|p|div|blockquote|section|article)\b[^>]*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<\s*li\b[^>]*>", "\n• ", text, flags=re.IGNORECASE)
    text = re.sub(r"<\s*/?(ul|ol)\b[^>]*>", "\n\n", text, flags=re.IGNORECASE)

    # 3. Strip remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # 4. Decode HTML entities
    text = html.unescape(text)
    # Replace non-breaking spaces
    text = text.replace("\xa0", " ")

    # 5. Normalize paragraph linebreaks:
    # Split by any series of whitespace/newlines and reconstruct cleanly
    lines = [line.strip() for line in text.splitlines()]
    
    # Group consecutive non-empty lines, separating paragraphs with \n\n
    paragraphs: list[str] = []
    current_para: list[str] = []

    for line in lines:
        if line:
            current_para.append(line)
        else:
            if current_para:
                paragraphs.append(" ".join(current_para))
                current_para = []

    if current_para:
        paragraphs.append(" ".join(current_para))

    # Join with standard double newlines (one blank line between paragraphs)
    return "\n\n".join(paragraphs).strip()
