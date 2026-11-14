"""
Zohra — Autonomous AI Article Generator & Publisher.

Uses ChatGPT / OpenAI (primary writing engine) to write comprehensive, high-quality,
evidence-grounded articles and publishes them live to Heavenly Insights.

Usage:
    python scripts/generate_and_publish.py
    python scripts/generate_and_publish.py --topic "How to Build a Daily Reading Habit" --category "Books"
    python scripts/generate_and_publish.py --topic "The Future of Autonomous AI Agents in 2026" --category "Technology"
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import get_settings  # noqa: E402
from app.integrations.heavenly.client import HeavenlyClient  # noqa: E402
from app.integrations.heavenly.formatter import format_plain_text_body  # noqa: E402
from app.llm.base import LLMRequest  # noqa: E402
from app.llm.registry import get_default_provider  # noqa: E402


def generate_slug(text: str) -> str:
    """Creates a clean, URL-safe slug from title."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


async def generate_article_content(topic: str, category: str) -> dict[str, str]:
    """Uses Gemini LLM to write a comprehensive, professional article."""
    provider = get_default_provider()
    print(f"[*] Calling AI Engine ({provider.name}) to write full article...")

    prompt = f"""
You are Zohra's Senior Chief Editor and World-Class Knowledge Writer.
Write a comprehensive, engaging, deeply practical, and authoritative blog post on the topic:
"{topic}"

Structure your response using these exact section markers:

===TITLE===
[Engaging, clear, SEO-friendly headline]

===SLUG===
[url-friendly-slug-with-hyphens]

===CATEGORY===
{category}

===EXCERPT===
[A compelling 2-sentence summary hook that draws readers in]

===BODY===
[The complete full-length article: 700 to 1000 words.
Include:
- An engaging, relatable introduction.
- Core psychological and practical principles (e.g., micro-habits, environmental design, habit stacking).
- Clear subheadings on their own line for each section.
- Actionable step-by-step guidance.
- Practical strategies to overcome reading slumps and friction.
- Inspiring closing reflection.
Format: Clean plain text prose. Separate all sections and paragraphs with a blank line (double newline). Do not use HTML tags.]
"""

    req = LLMRequest(
        prompt=prompt,
        role="writing",
        temperature=0.7,
        max_tokens=4000,
    )

    response = await provider.generate(req)
    raw = response.content.strip()

    title = topic
    slug = generate_slug(topic)
    cat = category
    excerpt = f"A practical and comprehensive guide to {topic}."
    body = raw

    # Parse markers cleanly
    if "===TITLE===" in raw and "===BODY===" in raw:
        def extract_between(text: str, start_tag: str, end_tags: list[str]) -> str:
            if start_tag not in text:
                return ""
            part = text.split(start_tag, 1)[1]
            closest_idx = len(part)
            for et in end_tags:
                idx = part.find(et)
                if idx != -1 and idx < closest_idx:
                    closest_idx = idx
            return part[:closest_idx].strip()

        t_val = extract_between(raw, "===TITLE===", ["===SLUG===", "===CATEGORY===", "===EXCERPT===", "===BODY==="])
        if t_val:
            title = t_val

        s_val = extract_between(raw, "===SLUG===", ["===CATEGORY===", "===EXCERPT===", "===BODY==="])
        if s_val:
            slug = generate_slug(s_val)

        c_val = extract_between(raw, "===CATEGORY===", ["===EXCERPT===", "===BODY==="])
        if c_val:
            cat = c_val

        e_val = extract_between(raw, "===EXCERPT===", ["===BODY==="])
        if e_val:
            excerpt = e_val

        if "===BODY===" in raw:
            body = raw.split("===BODY===", 1)[1].strip()

    return {
        "title": title,
        "slug": slug,
        "category": cat,
        "excerpt": excerpt,
        "body": format_plain_text_body(body),
    }


async def main():
    parser = argparse.ArgumentParser(description="Zohra AI Article Writer & Heavenly Publisher")
    parser.add_argument(
        "--topic",
        default="How to Build a Daily Reading Habit",
        help="Topic to research and write about",
    )
    parser.add_argument(
        "--category",
        default="Books",
        help="Article category",
    )
    parser.add_argument(
        "--slug",
        default=None,
        help="Optional specific slug (defaults to slug generated from topic)",
    )
    parser.add_argument(
        "--draft",
        action="store_true",
        help="Save as draft instead of publishing live",
    )
    parser.add_argument(
        "--no-image",
        action="store_true",
        help="Skip automatic featured image generation",
    )
    args = parser.parse_args()


    print("=" * 68)
    print("  ZOHRA — AUTONOMOUS AI WRITER & HEAVENLY PUBLISHER")
    print("=" * 68)
    print(f"  Topic    : {args.topic}")
    print(f"  Category : {args.category}")
    print(f"  Mode     : {'DRAFT' if args.draft else 'PUBLISHED (LIVE)'}")
    print("=" * 68 + "\n")

    settings = get_settings()
    client = HeavenlyClient()

    if not client.is_configured:
        print("[!] Error: HEAVENLY_API_TOKEN is not configured in .env")
        sys.exit(1)

    # 1. Generate full article via AI
    article = await generate_article_content(topic=args.topic, category=args.category)
    if args.slug:
        article["slug"] = args.slug

    print(f"\n[+] Article Generated Successfully!")
    print(f"    - Title   : {article['title']}")
    print(f"    - Slug    : {article['slug']}")
    print(f"    - Words   : ~{len(article['body'].split())} words")
    print(f"    - Excerpt : {article['excerpt']}")

    # 2. Automatically Generate, Validate, Upload & Optimize Featured Image
    featured_image_url = None
    featured_image_alt = None
    image_bytes = None
    if not getattr(args, "no_image", False):
        print(f"\n[*] Automatically Generating, Validating & Uploading Featured Image...")
        for media_attempt in range(1, 4):
            image_bytes = None
            featured_image_url = None
            media_res: dict = {}
            try:
                from app.publishing.media import ImageProvider
                media_res = await ImageProvider.generate_article_featured_image(
                    title=article["title"],
                    topic=args.topic,
                    category=article["category"],
                    audience="Learners and Practitioners",
                    tone="Authoritative and Practical",
                    full_text=article["body"],
                )
                image_bytes = media_res.get("bytes")
                featured_image_alt = media_res.get("alt_text") or f"Editorial visual for {article['title']}"
                print(f"[+] Featured Image Generated & Optimized:")
                print(f"    - Filename : {media_res.get('filename')}")
                print(f"    - Dimensions: {media_res.get('width')}x{media_res.get('height')}")
                print(f"    - Alt Text : \"{featured_image_alt}\"")
                print(f"    - Quality  : {media_res.get('relevance_score')} (Passed: {media_res.get('validation_passed')})")
                print(f"    - Provider : {media_res.get('provider')} ({media_res.get('source_type')})")
            except Exception as e:
                print(f"[!] Warning: Image generation error (attempt {media_attempt}): {e}")

            if image_bytes:
                try:
                    # A local "/storage/..." path is meaningless on the live blog;
                    # the image must be uploaded to obtain a public absolute URL.
                    featured_image_url = await client.ensure_public_cover_url(
                        image_bytes=image_bytes,
                        filename=media_res.get("filename") or f"{article['slug']}.webp",
                        mime_type="image/webp",
                    )
                    print(f"    - Public URL: {featured_image_url}")
                except Exception as up_exc:
                    print(f"[!] Cover upload error (attempt {media_attempt}): {up_exc}")

            if featured_image_url:
                break
            if media_attempt < 3:
                print(f"[~] Retrying media acquisition ({media_attempt}/3)...")

        if not featured_image_url and settings.ARTICLE_FEATURED_IMAGE_REQUIRED:
            print("[!] Publication aborted: every article must have a featured image.")
            sys.exit(1)

    # 3. Publish to Heavenly Insights
    status = "draft" if args.draft else "published"
    print(f"\n[*] Publishing to Heavenly Insights (status: '{status}')...")

    result = await client.create_or_update_post(
        title=article["title"],
        slug=article["slug"],
        category=article["category"],
        excerpt=article["excerpt"],
        body=article["body"],
        status=status,
        image_url=featured_image_url,
        cover_image_alt=featured_image_alt,
    )

    print("\n" + "=" * 68)
    print("  SUCCESSFULLY PUBLISHED TO HEAVENLY INSIGHTS!")
    print("=" * 68)

    article_url = result.get("url")
    if not article_url:
        article_url = f"{client.site_url}/articles/{article['slug']}"

    print(f"\n  >> Live Article URL: {article_url} <<")
    if featured_image_url:
        print(f"  >> Featured Image Attached: {featured_image_url} <<\n")
    print("=" * 68)



if __name__ == "__main__":
    asyncio.run(main())
