"""
Zohra — Cover Image Backfill & Repair Tool.

Finds every article on the Heavenly Insights target that is missing a featured
image (``cover_image_url`` is null/empty) and attaches one, so that **no
published article is left imageless**.

How it works (verified against the live API):
  1. GET  /api/posts                     -> list every post
  2. for each post with no cover:
       ImageProvider.generate_article_featured_image(...)   -> real WebP bytes
       POST /api/images (multipart "file")                  -> public absolute URL
       POST /api/posts (same slug/title/body/category/status
                        + cover_image_url + cover_image_alt) -> attaches cover
  3. re-read and report which articles now have a cover

Safety:
  * Defaults to DRY RUN. Nothing is written unless ``--apply`` is passed.
  * The stored body is re-sent verbatim; the API formatter is byte-idempotent on
    existing bodies, so article text is never altered.
  * Title, slug, category, excerpt and status (published stays published) are
    preserved exactly.
  * Idempotent: re-running skips articles that already have a cover.

Usage:
    python scripts/backfill_covers.py                 # dry run, show the plan
    python scripts/backfill_covers.py --apply         # repair everything
    python scripts/backfill_covers.py --apply --limit 5
    python scripts/backfill_covers.py --apply --slug some-article-slug
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.integrations.heavenly.client import HeavenlyClient  # noqa: E402
from app.publishing.media import ImageProvider  # noqa: E402


async def fetch_posts(client: HeavenlyClient) -> list[dict]:
    """Reads every post (drafts + published) from the publisher."""
    async with httpx.AsyncClient(timeout=60.0) as http:
        resp = await http.get(client.api_url, headers=client._get_headers())
        resp.raise_for_status()
        data = resp.json()
    posts = data if isinstance(data, list) else data.get("posts", [])
    return [p for p in posts if isinstance(p, dict)]


def resolve_cover_url(post: dict, site_url: str) -> str | None:
    """Resolves a stored cover reference to a fetchable URL."""
    raw = (post.get("cover_image_url") or "").strip()
    if not raw:
        return None
    if raw.startswith(("http://", "https://")):
        return raw
    # Relative covers (e.g. "/article-covers/<slug>.webp") are served by the
    # publisher's own domain, so resolve them against it.
    return f"{site_url.rstrip('/')}/{raw.lstrip('/')}"


def has_cover(post: dict) -> bool:
    """
    True when the post already carries a cover reference.

    Note: a relative cover such as "/article-covers/<slug>.webp" is legitimate
    here — unlike Zohra's own "/storage/..." paths, the publisher does serve it.
    """
    return bool((post.get("cover_image_url") or "").strip())


async def is_fetchable(url: str, attempts: int = 3, timeout: float = 20.0) -> tuple[bool, str]:
    """
    Checks a cover URL resolves for an anonymous reader.

    Retries because the publisher throttles bursts of rapid requests, which
    otherwise shows up as false "broken cover" reports.
    """
    last = "no attempt"
    for attempt in range(1, attempts + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as http:
                resp = await http.get(url)
            if resp.status_code == 200 and resp.content:
                return True, "200"
            last = f"HTTP {resp.status_code}"
        except Exception as exc:  # noqa: BLE001
            last = f"{type(exc).__name__}: {exc}"
        if attempt < attempts:
            await asyncio.sleep(1.5 * attempt)
    return False, last


async def build_cover_for(post: dict, client: HeavenlyClient) -> tuple[str | None, dict]:
    """Generates + uploads a cover for one post. Returns (public_url, metadata)."""
    title = (post.get("title") or "").strip()
    media = await ImageProvider.generate_article_featured_image(
        title=title,
        topic=post.get("category") or "General",
        category=post.get("category") or "General",
        full_text=post.get("body") or "",
    )

    meta = {
        "provider": media.get("provider"),
        "source_type": media.get("source_type"),
        "relevance_score": media.get("relevance_score"),
        "width": media.get("width"),
        "height": media.get("height"),
    }

    public_url = await client.ensure_public_cover_url(
        image_bytes=media.get("bytes"),
        candidate_url=media.get("public_url"),
        filename=media.get("filename") or "cover.webp",
    )
    meta["alt_text"] = media.get("alt_text")
    return public_url, meta


async def run(args: argparse.Namespace) -> int:
    client = HeavenlyClient()
    if not client.is_configured:
        print("[!] HEAVENLY_API_TOKEN is not configured in .env")
        return 1

    print("=" * 74)
    print("  ZOHRA — COVER IMAGE BACKFILL" + ("" if args.apply else "  (DRY RUN — no writes)"))
    print("=" * 74)
    print(f"  Target : {client.site_url}")

    posts = await fetch_posts(client)
    print(f"  Posts  : {len(posts)} total")

    covered = [p for p in posts if has_cover(p)]
    missing = [p for p in posts if not has_cover(p)]

    # Optionally re-verify that existing covers really resolve for readers.
    broken: list[dict] = []
    if args.verify_existing:
        print(f"  Verifying {len(covered)} existing covers...")
        for p in covered:
            url = resolve_cover_url(p, client.site_url)
            if not url:
                continue
            ok, detail = await is_fetchable(url)
            if not ok:
                broken.append(p)
                print(f"    [!] {p.get('slug')} -> {detail}")
            await asyncio.sleep(0.2)  # be polite; avoids throttle false positives
        print(f"  Broken existing covers: {len(broken)}")

    if args.slug:
        missing = [p for p in missing if p.get("slug") == args.slug]
        broken = [p for p in broken if p.get("slug") == args.slug]
    if args.limit:
        missing = missing[: args.limit]
        broken = broken[: args.limit]

    targets = missing + broken
    print(f"  With cover    : {len(covered)}")
    print(f"  Missing cover : {len(missing)}")
    if args.verify_existing:
        print(f"  Broken cover  : {len(broken)}")
    print(f"  To process    : {len(targets)}")
    print("=" * 74)

    if not targets:
        print("\n[+] Nothing to do — every article already has a working cover image.")
        return 0

    for i, post in enumerate(targets, 1):
        slug = post.get("slug") or "<no-slug>"
        reason = "missing" if not has_cover(post) else "broken URL"
        print(f"\n[{i}/{len(targets)}] {slug}  ({reason})")
        print(f"    title  : {(post.get('title') or '')[:72]}")
        print(f"    status : {post.get('status')}")

        if not args.apply:
            print("    -> would generate + upload a cover and re-post with it")
            continue

        try:
            public_url, meta = await build_cover_for(post, client)
            if not public_url:
                print("    [!] FAILED: no public cover URL produced")
                continue

            await client.create_or_update_post(
                title=post.get("title") or slug,
                slug=slug,
                category=post.get("category") or "General",
                excerpt=post.get("excerpt") or "",
                body=post.get("body") or "",
                status=post.get("status") or "published",
                image_url=public_url,
                cover_image_alt=meta.get("alt_text"),
            )
            print(f"    [+] cover attached: {public_url}")
            print(f"        provider={meta.get('provider')} score={meta.get('relevance_score')}")

            if (post.get("status") or "").lower() == "published":
                ok = await client.verify_cover_image_public(public_url)
                print(f"        publicly fetchable: {ok}")

        except Exception as exc:  # noqa: BLE001
            print(f"    [!] ERROR: {exc}")

    if args.apply:
        print("\n" + "=" * 74)
        print("  RE-CHECK")
        print("=" * 74)
        posts_after = await fetch_posts(client)
        still = [p.get("slug") for p in posts_after if not has_cover(p)]
        print(f"  Posts          : {len(posts_after)}")
        print(f"  Still imageless: {len(still)}")
        if still:
            for s in still[:20]:
                print(f"    - {s}")

    print()
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill missing article cover images")
    parser.add_argument("--apply", action="store_true", help="Actually write changes (default is dry run)")
    parser.add_argument("--limit", type=int, default=None, help="Process at most N articles")
    parser.add_argument("--slug", type=str, default=None, help="Only process this slug")
    parser.add_argument(
        "--verify-existing",
        action="store_true",
        help="Also fetch every existing cover and repair any that no longer resolve",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
