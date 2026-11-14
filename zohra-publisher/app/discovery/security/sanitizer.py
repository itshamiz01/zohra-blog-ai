"""
Zohra — Content Sanitizer.

Cleans untrusted external HTML/text:
- Strips dangerous tags (script, style, iframe, form, object, embed, etc.)
- Strips inline JS event handlers (onclick, onload, etc.)
- Strips zero-width and invisible unicode characters
- Normalizes unicode into NFKC form
- Collapses whitespace and control characters safely
"""

from __future__ import annotations

import html
import re
import unicodedata

# Dangerous tags whose content must be discarded entirely
DANGEROUS_TAGS_RE = re.compile(
    r"<(script|style|iframe|object|embed|form|applet|svg|meta|link)[^>]*>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)

# Inline event handlers and javascript: URIs
EVENT_HANDLERS_RE = re.compile(r"""on\w+\s*=\s*(['"]).*?\1""", re.IGNORECASE)
JS_URIS_RE = re.compile(r"""href\s*=\s*(['"])javascript:.*?\1""", re.IGNORECASE)

# HTML tags to strip while keeping their inner text
ANY_TAG_RE = re.compile(r"<[^>]+>")

# Zero-width and invisible unicode characters (including soft hyphen)
INVISIBLE_CHARS_RE = re.compile(
    r"[\u200B-\u200D\uFEFF\u2060\u00A0\u180E\u2000-\u200A\u202F\u205F\u3000\u00AD]"
)

# Control characters except regular newline and tab
CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]")


def clean_html(raw_html: str) -> str:
    """
    Remove all script/style elements, strip all HTML tags,
    decode HTML entities, and return clean plaintext.
    """
    if not raw_html or not isinstance(raw_html, str):
        return ""

    # 1. Remove dangerous blocks completely (including their contents)
    cleaned = DANGEROUS_TAGS_RE.sub(" ", raw_html)

    # 2. Break common block tags into newlines before stripping
    cleaned = re.sub(r"<(p|div|br|h[1-6]|li|tr)[^>]*>", "\n", cleaned, flags=re.IGNORECASE)

    # 3. Strip remaining tags
    cleaned = ANY_TAG_RE.sub(" ", cleaned)

    # 4. Decode HTML entities
    cleaned = html.unescape(cleaned)

    # 5. Sanitize text
    return sanitize_text(cleaned)


def sanitize_text(text: str) -> str:
    """
    Sanitizes plain text:
    - Normalizes Unicode (NFKC)
    - Replaces invisible characters with regular spaces
    - Strips control characters
    - Normalizes consecutive spaces and lines
    """
    if not text or not isinstance(text, str):
        return ""

    # 1. Unicode normalization (NFKC)
    norm = unicodedata.normalize("NFKC", text)

    # 2. Replace invisible characters with normal space
    norm = INVISIBLE_CHARS_RE.sub(" ", norm)

    # 3. Remove non-printable control characters
    norm = CONTROL_CHARS_RE.sub("", norm)

    # 4. Collapse multiple spaces within lines
    lines = []
    for line in norm.splitlines():
        clean_line = re.sub(r"[ \t]+", " ", line).strip()
        if clean_line:
            lines.append(clean_line)

    # 5. Join with maximum 2 consecutive newlines
    return "\n\n".join(lines).strip()


class ContentSanitizer:
    sanitize_html = staticmethod(clean_html)
    clean_text = staticmethod(sanitize_text)
    sanitize_text = staticmethod(sanitize_text)

