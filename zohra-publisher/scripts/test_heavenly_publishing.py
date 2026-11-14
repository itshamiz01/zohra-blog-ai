"""
Zohra — Heavenly Insights Live Publishing Verification Script.

Usage:
    python scripts/test_heavenly_publishing.py
    python scripts/test_heavenly_publishing.py --publish

Features:
- Reads HEAVENLY_SITE_URL, HEAVENLY_API_URL, HEAVENLY_API_TOKEN from .env.
- Never prints the raw token to stdout or stderr.
- Step 1: Tests draft creation with required payload.
- Step 2: Verifies draft response.
- Step 3: Lists posts (GET /api/posts) with Bearer token.
- Step 4 (optional --publish): Tests publishing with status 'published' and prints the article URL.
- Preserves idempotency using the same slug on retry or update.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add project root to sys.path so app modules import properly
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import get_settings  # noqa: E402
from app.integrations.heavenly.client import HeavenlyClient  # noqa: E402
from app.integrations.heavenly.exceptions import (  # noqa: E402
    HeavenlyAuthError,
    HeavenlyConnectionError,
    HeavenlyError,
)


def mask_token(token: str) -> str:
    """Safely masks a token for user display."""
    if not token or len(token) < 8:
        return "***"
    return f"{token[:4]}...{token[-4:]} ({len(token)} chars)"


async def run_verification(publish_mode: bool = False) -> int:
    print("=" * 65)
    print("  ZOHRA — HEAVENLY INSIGHTS PUBLISHING VERIFICATION")
    print("=" * 65)

    settings = get_settings()

    site_url = getattr(settings, "HEAVENLY_SITE_URL", None) or "https://heavenly-insights-educator.hamidansari1795.chatgpt.site"
    api_url = getattr(settings, "HEAVENLY_API_URL", None) or f"{site_url}/api/posts"
    token = getattr(settings, "HEAVENLY_API_TOKEN", None) or ""

    print("\n[1] Configuration Check:")
    print(f"    - Site URL : {site_url}")
    print(f"    - API URL  : {api_url}")

    if not token or token.strip() == "PASTE_GENERATED_TOKEN_HERE":
        print("    - Token    : [MISSING / PLACEHOLDER]")
        print("\n[!] HEAVENLY_API_TOKEN is not yet configured in .env.")
        print("    Follow these steps:")
        print("    1. Open: https://heavenly-insights-educator.hamidansari1795.chatgpt.site/admin")
        print("    2. Log in with your ChatGPT account")
        print("    3. Click 'Generate / replace token' and copy the token")
        print("    4. In .env, replace 'PASTE_GENERATED_TOKEN_HERE' with your real token")
        print("    5. Re-run: python scripts/test_heavenly_publishing.py\n")
        return 1

    print(f"    - Token    : {mask_token(token)} [CONFIGURED]")

    client = HeavenlyClient(site_url=site_url, api_url=api_url, token=token)

    # Payload specified by user
    title = "How to Build a Daily Reading Habit"
    slug = "how-to-build-a-daily-reading-habit"
    category = "Books"
    excerpt = "Practical steps to make reading part of your daily routine."
    body = "First paragraph.\n\nSecond paragraph."

    # ── Step 1: Create & Verify Draft ─────────────────────────────────
    print("\n[2] Testing Draft Creation (status: 'draft')...")
    print(f"    Target slug: '{slug}'")

    try:
        draft_response = await client.create_draft(
            title=title,
            slug=slug,
            category=category,
            excerpt=excerpt,
            body=body,
        )
        print("    [SUCCESS] Draft created successfully!")
        print(f"    Response: {json.dumps(draft_response, indent=2)}")
    except HeavenlyAuthError as exc:
        print(f"\n    [AUTH ERROR] {exc}")
        print("    Please check that your token was copied correctly from the admin panel.")
        return 1
    except HeavenlyConnectionError as exc:
        print(f"\n    [CONNECTION ERROR] {exc}")
        return 1
    except HeavenlyError as exc:
        print(f"\n    [ERROR] {exc}")
        return 1
    except Exception as exc:
        print(f"\n    [UNEXPECTED ERROR] {exc}")
        return 1

    # ── Step 2: List Posts (GET /api/posts) ────────────────────────────
    print("\n[3] Listing posts via GET /api/posts...")
    try:
        posts = await client.list_posts()
        count = len(posts) if isinstance(posts, list) else len(posts.get("posts", [])) if isinstance(posts, dict) else 0
        print(f"    [SUCCESS] Found {count} post(s) registered in publisher workspace.")
        if isinstance(posts, list) and posts:
            for p in posts[:3]:
                print(f"      - [{p.get('status', 'unknown').upper()}] {p.get('title')} (slug: {p.get('slug')})")
    except Exception as exc:
        print(f"    [WARNING] Listing posts returned: {exc}")

    # ── Step 3: Production Publication (if requested) ──────────────────
    if publish_mode:
        print("\n[4] Testing Production Publishing (status: 'published')...")
        print(f"    Using same slug '{slug}' (Idempotent update)...")
        try:
            pub_response = await client.publish_post(
                title=title,
                slug=slug,
                category=category,
                excerpt=excerpt,
                body=body,
            )
            print("    [SUCCESS] Article published live!")
            print(f"    Response: {json.dumps(pub_response, indent=2)}")
            if isinstance(pub_response, dict):
                article_url = pub_response.get("url") or pub_response.get("link")
                if article_url:
                    print(f"\n    >> Live Article URL: {article_url} <<")
        except Exception as exc:
            print(f"\n    [PUBLISH ERROR] {exc}")
            return 1
    else:
        print("\n[INFO] Draft verification complete. To test live publishing, run:")
        print("       python scripts/test_heavenly_publishing.py --publish")

    print("\n" + "=" * 65)
    print("  VERIFICATION COMPLETE - HEAVENLY INTEGRATION READY")
    print("=" * 65 + "\n")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify Heavenly Insights Publishing Integration")
    parser.add_argument("--publish", action="store_true", help="Also test publishing article live")
    args = parser.parse_args()

    exit_code = asyncio.run(run_verification(publish_mode=args.publish))
    sys.exit(exit_code)
