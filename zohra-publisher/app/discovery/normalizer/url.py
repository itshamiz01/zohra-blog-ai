"""
Zohra — Canonical URL Normalizer.

Normalizes URLs to ensure identical resources map to the exact same canonical URL:
- Strips analytics/tracking parameters (utm_*, fbclid, gclid, etc.)
- Normalizes protocol (lowercase)
- Lowercases host and strips default ports (:80, :443)
- Removes fragments (#section)
- Normalizes path slashes
- Sorts remaining query parameters deterministically
"""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

# Common tracking parameters to strip
TRACKING_PARAMS: set[str] = {
    # Google Analytics / Urchin
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
    "utm_source_platform",
    "utm_creative_format",
    "utm_marketing_tactic",
    # Facebook / Meta
    "fbclid",
    "fbadid",
    # Google Ads
    "gclid",
    "gclsrc",
    "dclid",
    "wbraid",
    "gbraid",
    # Microsoft / Bing
    "msclkid",
    # Mailchimp
    "mc_cid",
    "mc_eid",
    # HubSpot
    "_hsenc",
    "_hsmi",
    "hsCtaTracking",
    # Twitter / X
    "twclid",
    # Generic referral / tracking
    "ref",
    "ref_src",
    "source",
    "campaign",
    "feature",
    "spm",
}


def normalize_canonical_url(url: str) -> str:
    """
    Produce a deterministic canonical URL.
    Returns normalized string.
    """
    if not url or not isinstance(url, str):
        return ""

    url = url.strip()
    parsed = urlparse(url)

    scheme = parsed.scheme.lower()
    if not scheme:
        scheme = "https"

    # Hostname lowercase & strip default ports
    netloc = parsed.netloc.lower()
    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    elif netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]

    # Path normalization: collapse multiple slashes, strip trailing slash unless root, lowercase
    path = re.sub(r"/{2,}", "/", parsed.path).lower()
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    if not path:
        path = "/"

    # Strip /amp or .amp suffix if present
    if path.endswith("/amp"):
        path = path[:-4] or "/"

    # Filter tracking query parameters & sort remaining
    clean_params = []
    if parsed.query:
        for k, v in parse_qsl(parsed.query, keep_blank_values=False):
            if k.lower() not in TRACKING_PARAMS:
                clean_params.append((k, v))
        clean_params.sort(key=lambda x: (x[0], x[1]))

    clean_query = urlencode(clean_params)

    # Reconstruct URL without fragment
    return urlunparse((scheme, netloc, path, "", clean_query, ""))


class URLNormalizer:
    normalize = staticmethod(normalize_canonical_url)
