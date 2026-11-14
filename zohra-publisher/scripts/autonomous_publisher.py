"""
Zohra — 100% Autonomous AI Hardcore Brainstorming & Continuous Publishing Engine.

Features:
- Continuously triggers every 10 minutes (configurable via --interval).
- Live Global News & Intelligence Discovery (Google News, BBC, Ars Technica, NASA, Tech Feeds).
- Hardcore Multi-Angle Brainstorming Phase: Uncovers contrarian truths, first-principles analysis,
  psychological impact, and strategic playbooks.
- Masterpiece Article Generation: Writes beautifully styled, deeply engaging, 1000-1400 word articles.
- Auto-Publishes to Heavenly Insights live with persistent history deduplication.

Usage:
    python scripts/autonomous_publisher.py --interval 10
    python scripts/autonomous_publisher.py --interval 10 --category Technology
    python scripts/autonomous_publisher.py --once
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
import json
import logging
from pathlib import Path
import random
import re
import sys
import xml.etree.ElementTree as ET

import httpx

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import get_settings  # noqa: E402
from app.integrations.heavenly.client import HeavenlyClient  # noqa: E402
from app.integrations.heavenly.formatter import format_plain_text_body  # noqa: E402
from app.llm.base import LLMRequest  # noqa: E402
from app.llm.registry import get_default_provider  # noqa: E402

# Configuration
HISTORY_FILE = project_root / "data" / "published_history.json"

NEWS_FEEDS = {
    "Technology": [
        "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-US&gl=US&ceid=US:en",
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "https://feeds.arstechnica.com/arstechnica/index",
    ],
    "Science": [
        "https://news.google.com/rss/headlines/section/topic/SCIENCE?hl=en-US&gl=US&ceid=US:en",
        "https://www.nasa.gov/feed/",
    ],
    "Business": [
        "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-US&gl=US&ceid=US:en",
        "https://feeds.bbci.co.uk/news/business/rss.xml",
    ],
    "World Insights": [
        "https://news.google.com/rss/headlines/section/topic/WORLD?hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
    ],
}


def load_history() -> list[dict]:
    """Loads previously published articles to avoid duplicates."""
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_history(history: list[dict]) -> None:
    """Saves published article record."""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def generate_slug(text: str) -> str:
    """Generates a clean URL slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")[:80]


async def fetch_trending_headlines(category: str | None = None) -> list[dict[str, str]]:
    """Fetches real-time headlines from verified RSS and Google News feeds."""
    headlines = []
    target_categories = [category] if category and category in NEWS_FEEDS else list(NEWS_FEEDS.keys())

    async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
        for cat in target_categories:
            urls = NEWS_FEEDS.get(cat, [])
            for url in urls:
                try:
                    resp = await client.get(
                        url,
                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Zohra/1.0"},
                    )
                    if resp.status_code == 200:
                        root = ET.fromstring(resp.text)
                        for item in root.findall(".//item")[:15]:
                            title_elem = item.find("title")
                            link_elem = item.find("link")
                            pub_elem = item.find("pubDate")
                            desc_elem = item.find("description")

                            if title_elem is not None and title_elem.text:
                                raw_title = title_elem.text.strip()
                                clean_title = re.sub(r"\s+-\s+[A-Za-z0-9\s\.\&]+$", "", raw_title).strip()
                                headlines.append({
                                    "title": clean_title,
                                    "category": cat,
                                    "source_url": link_elem.text if link_elem is not None else "",
                                    "published_at": pub_elem.text if pub_elem is not None else "",
                                    "snippet": (desc_elem.text if desc_elem is not None and desc_elem.text else "")[:200],
                                })
                except Exception:
                    continue

    return headlines


async def hardcore_brainstorming(
    headlines: list[dict[str, str]],
    history: list[dict],
) -> dict[str, any]:
    """
    Hardcore Brainstorming Engine:
    Takes live trends, explores multiple angles (contrarian truth, human psychology, 10-year outlook, tactical playbook),
    and synthesizes a masterpiece article concept.
    """
    provider = get_default_provider()

    past_titles = [h.get("title", "") for h in history[-40:]]
    past_topics_summary = "\n".join(f"- {t}" for t in past_titles) if past_titles else "None yet."

    random.shuffle(headlines)
    selected_headlines = headlines[:25]
    headlines_summary = "\n".join(f"- [{h['category']}] {h['title']}" for h in selected_headlines)

    brainstorm_prompt = f"""
You are the Executive Director of an elite intellectual think tank and editorial publication.
We need a HARDCORE BRAINSTORMING session based on real-time world events.

LIVE REAL-TIME BREAKING HEADLINES:
{headlines_summary}

TOPICS ALREADY PUBLISHED (DO NOT REPEAT OR CLOSELY CLONE):
{past_topics_summary}

PERFORM DEEP HARDCORE BRAINSTORMING:
1. Look beyond surface headlines. What underlying shift, paradox, economic tremor, or technological breakthrough is actually unfolding?
2. Brainstorm 3 distinct, brilliant angles:
   - Angle A (The Hidden Undercurrent): What is everyone misunderstanding or ignoring about this story?
   - Angle B (The Human & Psychological Dimension): How does this redefine how humans live, think, or work?
   - Angle C (The First-Principles Playbook): What strategic insights, lessons, or mental models should readers adopt?
3. Select the single most profound, beautiful, and magnetic topic that combines timely relevance with timeless wisdom.

Respond strictly in this JSON format:
{{
  "brainstormed_angles": [
    {{"angle": "Angle A description"}},
    {{"angle": "Angle B description"}},
    {{"angle": "Angle C description"}}
  ],
  "chosen_angle_rationale": "Why this specific topic will captivate and educate readers",
  "article_topic": "The captivating, intellectual, SEO-strong title for the article",
  "category": "Technology | Science | Business | Personal Growth | World Insights",
  "core_themes": ["Theme 1", "Theme 2", "Theme 3"]
}}
"""

    req = LLMRequest(
        prompt=brainstorm_prompt,
        role="brainstorming",
        temperature=0.8,
        max_tokens=1500,
        response_format={"type": "json_object"},
    )

    response = await provider.generate(req)
    raw = response.content.strip()

    try:
        data = None
        try:
            data = json.loads(raw)
        except Exception:
            json_match = re.search(r"\{.*\}", raw, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))

        if isinstance(data, dict):
            topic = (
                data.get("article_topic")
                or data.get("topic")
                or data.get("title")
                or data.get("chosen_trend")
                or ""
            ).strip()
            cat = data.get("category", "Technology").strip()
            rationale = data.get("chosen_angle_rationale") or data.get("rationale") or ""
            angles = data.get("brainstormed_angles", [])
            themes = data.get("core_themes", [])

            if topic:
                return {
                    "topic": topic,
                    "category": cat,
                    "rationale": rationale,
                    "angles": angles,
                    "themes": themes,
                }
    except Exception:
        pass

    # High-quality fallback
    for h in selected_headlines:
        if h["title"] not in past_titles:
            return {
                "topic": f"Beyond the Noise: The Deeper Implications of {h['title']}",
                "category": h["category"],
                "rationale": "High-impact real-time analysis",
                "angles": [],
                "themes": ["First Principles", "Strategic Foresight"],
            }

    return {
        "topic": "The Invisible Architecture: How Autonomous Systems are Reshaping Global Commerce",
        "category": "Technology",
        "rationale": "Evergreen high-leverage intellectual insight",
        "angles": [],
        "themes": ["Automation", "Economics", "Future of Work"],
    }


async def generate_beautiful_article(
    topic: str,
    category: str,
    brainstorm_context: dict[str, any],
) -> dict[str, str]:
    """
    Generates a beautifully structured, authoritative, publication-ready article
    between 1000 and 1400 words with rich narrative cadence and practical depth.
    """
    provider = get_default_provider()

    rationale = brainstorm_context.get("rationale", "")
    themes = ", ".join(brainstorm_context.get("themes", []))

    prompt = f"""
You are Zohra's Master Essayist and World-Class Knowledge Writer.
Your task is to write an exceptionally beautiful, intellectually rich, deeply researched blog article.

TOPIC: "{topic}"
CATEGORY: {category}
EDITORIAL FOCUS: {rationale}
CORE THEMES: {themes}

WRITING STANDARDS FOR A MASTERPIECE:
1. THE COLD OPEN: Start with an evocative, cinematic hook that immediately immerses the reader into the tension, discovery, or paradox of the topic. No generic "In today's fast-paced world..." openings.
2. NARRATIVE CADENCE: Write with rhythm, clarity, and intellectual elegance. Use vivid metaphors and crisp analytical reasoning.
3. FIRST-PRINCIPLES SUBSTANCE: Explain the 'Why' behind the 'What'. Break down underlying mechanics, human psychology, or systemic incentives.
4. ACTIONABLE CLARITY: Include concrete takeaways, strategic mental models, or practical frameworks the reader can apply.
5. BEAUTIFUL STRUCTURE & LENGTH REQUIREMENT:
   - CRITICAL: Write a long, comprehensive, in-depth article between 1000 to 1400 words. Do NOT summarize or write a brief overview.
   - Develop 5 to 6 full, multi-paragraph sections.
   - Use clear, captivating section subheadings (placed on their own line with blank lines above and below).
   - Use bullet points for structured breakdowns and key rules.
   - Conclude with a memorable, philosophical, and inspiring closing reflection.
   - Format: Pure clean text prose with double newlines between paragraphs. No HTML tags. No markdown '#' symbols for headers, just clean title lines.
   - Use clear, captivating section subheadings (placed on their own line with blank lines above and below).
   - Use bullet points for structured breakdowns and key rules.
   - Conclude with a memorable, philosophical, and inspiring closing reflection.
   - Format: Pure clean text prose with double newlines between paragraphs. No HTML tags. No markdown '#' symbols for headers, just clean title lines.

STRUCTURE YOUR OUTPUT WITH THESE EXACT TAGS:

===TITLE===
[Captivating, refined, high-engagement headline]

===SLUG===
[clean-url-safe-slug]

===CATEGORY===
{category}

===EXCERPT===
[A gripping 2-sentence hook that compels the reader to click]

===BODY===
[The complete, full-length beautiful article]
"""

    req = LLMRequest(
        prompt=prompt,
        role="writing",
        temperature=0.75,
        max_tokens=4000,
    )

    response = await provider.generate(req)
    raw = response.content.strip()

    title = topic
    slug = generate_slug(topic)
    cat = category
    excerpt = f"An in-depth exploration of {topic}."
    body = raw

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


async def run_single_autonomous_cycle(
    client: HeavenlyClient,
    category_filter: str | None = None,
    mode: str = "published",
) -> dict | None:
    """Executes one full autonomous cycle with hardcore brainstorming."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*75}")
    print(f"  [AUTONOMOUS CYCLE TRIGGERED] — {now_str}")
    print(f"{'='*75}")

    history = load_history()

    # Step 1: Scan real-time global trends
    print("[1/4] Scanning live global trends from Google News, BBC, and Tech feeds...")
    headlines = await fetch_trending_headlines(category=category_filter)
    if not headlines:
        print("  [!] Warning: Using fallback high-leverage intellectual seeds.")
        headlines = [
            {"title": "The Rise of Agentic Reasoning and Self-Reflective Systems", "category": "Technology"},
            {"title": "The Quantum Computing Transition in Financial Infrastructure", "category": "Business"},
            {"title": "Biological Computation and the Next Wave of Synthetic Intelligence", "category": "Science"},
        ]
    print(f"  -> Discovered {len(headlines)} fresh global trends & news stories.")

    # Step 2: Hardcore Brainstorming
    print("\n[2/4] Executing Hardcore Brainstorming (Angle Discovery & First-Principles Analysis)...")
    brainstorm = await hardcore_brainstorming(headlines, history)
    topic = brainstorm["topic"]
    category = brainstorm["category"]
    rationale = brainstorm.get("rationale", "")
    angles = brainstorm.get("angles", [])
    themes = brainstorm.get("themes", [])

    if angles:
        print("  -> Brainstormed Angles:")
        for idx, a in enumerate(angles, 1):
            ang_text = a.get("angle", "")
            print(f"     {idx}. {ang_text}")

    print(f"  -> Selected Master Topic: \"{topic}\"")
    print(f"  -> Category             : {category}")
    if themes:
        print(f"  -> Core Themes          : {', '.join(themes)}")
    if rationale:
        print(f"  -> Strategic Rationale  : {rationale}")

    provider = get_default_provider()
    model_name = provider.get_model_for_role("writing") if hasattr(provider, "get_model_for_role") else "default"

    # Step 3: Write Beautiful Article
    print(f"\n[3/5] {provider.name.title()} writing master-class article (1000-1400 words)...")
    article = await generate_beautiful_article(topic, category, brainstorm)
    words = len(article["body"].split())
    print(f"  -> Article Generated: \"{article['title']}\" ({words} words)")
    print(f"  -> Excerpt          : {article['excerpt']}")

    # Step 4: Automatic Article Image Generation, Validation, Upload & Optimization
    print(f"\n[4/5] Generating, Validating, Uploading & Optimizing Featured Hero Image...")
    featured_image_url = None
    featured_image_alt = None
    image_metadata = {}
    image_bytes = None

    max_media_attempts = 3
    for media_attempt in range(1, max_media_attempts + 1):
        image_bytes = None
        featured_image_url = None
        try:
            from app.publishing.media import ImageProvider

            media_res = await ImageProvider.generate_article_featured_image(
                title=article["title"],
                topic=topic,
                category=category,
                audience="Learners and Thinkers",
                tone="Authoritative and Practical",
                full_text=article["body"],
            )
            image_bytes = media_res.get("bytes")
            featured_image_alt = media_res.get("alt_text") or f"Editorial visual for {article['title']}"
            image_metadata = {
                "filename": media_res.get("filename"),
                "width": media_res.get("width"),
                "height": media_res.get("height"),
                "relevance_score": media_res.get("relevance_score"),
                "content_hash": media_res.get("content_hash"),
                "cost": media_res.get("cost"),
                "provider": media_res.get("provider"),
                "source_type": media_res.get("source_type"),
                "attempt": media_attempt,
            }
            if image_bytes:
                print(
                    f"  -> Featured Image Ready: {media_res.get('filename')} "
                    f"({media_res.get('width')}x{media_res.get('height')})"
                )
                print(f"  -> Alt Text: \"{featured_image_alt}\"")
                print(
                    f"  -> Quality / Relevance Score: {media_res.get('relevance_score')} "
                    f"(Passed: {media_res.get('validation_passed')}, provider: {media_res.get('provider')})"
                )
            else:
                print(f"  [!] Image engine returned no bytes (status={media_res.get('status')}).")
        except Exception as img_exc:
            print(f"  [!] Featured image generation error (attempt {media_attempt}): {img_exc}")

        # 4b. Upload to the target site to obtain a PUBLIC absolute URL.
        # The Heavenly API only reads `cover_image_url`; a local "/storage/..." path
        # resolves to nothing on the live blog, which is why covers used to vanish.
        if image_bytes:
            try:
                featured_image_url = await client.ensure_public_cover_url(
                    image_bytes=image_bytes,
                    filename=image_metadata.get("filename") or f"{article['slug']}.webp",
                    mime_type="image/webp",
                )
                image_metadata["public_url"] = featured_image_url
                print(f"  -> Cover uploaded and publicly hosted: {featured_image_url}")
            except Exception as up_exc:
                print(f"  [!] Cover upload error (attempt {media_attempt}): {up_exc}")

        if featured_image_url:
            break

        if media_attempt < max_media_attempts:
            print(f"  [~] Retrying media acquisition ({media_attempt}/{max_media_attempts})...")
            await asyncio.sleep(3 * media_attempt)

    # Project invariant: NO article is ever published without a cover image.
    if not featured_image_url:
        settings = get_settings()
        if getattr(settings, "ARTICLE_FEATURED_IMAGE_REQUIRED", True):
            raise RuntimeError(
                "Refusing to publish without a featured image "
                f"(generated_bytes={'yes' if image_bytes else 'no'}). "
                "The cycle will retry so the article is never posted imageless."
            )

    # Step 5: Publish Live
    print(f"\n[5/5] Publishing to Heavenly Insights (status: '{mode}')...")
    result = await client.create_or_update_post(
        title=article["title"],
        slug=article["slug"],
        category=article["category"],
        excerpt=article["excerpt"],
        body=article["body"],
        status=mode,
        image_url=featured_image_url,
        cover_image_alt=featured_image_alt,
    )

    article_url = result.get("url") or f"{client.site_url}/articles/{article['slug']}"
    print(f"\n  {'*'*70}")
    print(f"  >>> LIVE ARTICLE POSTED: {article_url} <<<")

    # Post-publish proof that the cover is actually visible to readers.
    # An uploaded image only becomes public once a published post references it.
    cover_verified = False
    if featured_image_url and mode == "published":
        cover_verified = await client.verify_cover_image_public(featured_image_url)
        status_label = "VERIFIED PUBLIC" if cover_verified else "NOT YET PUBLIC (check manually)"
        print(f"  >>> FEATURED IMAGE ATTACHED: {featured_image_url} [{status_label}] <<<")
    elif featured_image_url:
        print(f"  >>> FEATURED IMAGE ATTACHED (draft): {featured_image_url} <<<")
    print(f"  {'*'*70}\n")

    # Record history
    record = {
        "title": article["title"],
        "slug": article["slug"],
        "category": article["category"],
        "url": article_url,
        "status": mode,
        "words": words,
        "featured_image_url": featured_image_url,
        "featured_image_alt": featured_image_alt,
        "cover_verified_public": cover_verified,
        "image_metadata": image_metadata,
        "published_at": datetime.now().isoformat(),
    }
    history.append(record)
    save_history(history)


    print(f"  -> Saved in history ({len(history)} total articles published).")
    return record


async def autonomous_loop(
    interval_minutes: int = 10,
    category: str | None = None,
    mode: str = "published",
    max_cycles: int | None = None,
):
    """Continuous autonomous loop triggered every N minutes."""
    prov = get_default_provider()
    prov_model = prov.get_model_for_role("writing") if hasattr(prov, "get_model_for_role") else "default"
    essayist_label = f"{prov.name.title()} ({prov_model})"

    print(f"""
========================================================================
   ZOHRA AUTONOMOUS RESEARCH & PUBLISHING OS — 24/7 AGENT
========================================================================
  Trigger Frequency : Every {interval_minutes} minutes
  Intelligence Mode : Hardcore Multi-Angle Brainstorming
  AI Essayist       : {essayist_label}
  Live Publishing   : Heavenly Insights Educator ({mode.upper()})
  Duplicate Guard   : Active (Local History Deduplication)
========================================================================
    """)

    client = HeavenlyClient()
    if not client.is_configured:
        print("[!] Error: HEAVENLY_API_TOKEN is not configured in .env")
        sys.exit(1)

    cycles_completed = 0
    sleep_seconds = interval_minutes * 60

    while True:
        try:
            await run_single_autonomous_cycle(
                client=client,
                category_filter=category,
                mode=mode,
            )
            cycles_completed += 1

            if max_cycles and cycles_completed >= max_cycles:
                print(f"\n[+] Completed requested {max_cycles} cycles. Exiting.")
                break

            # Sleep countdown
            next_run_dt = datetime.fromtimestamp(datetime.now().timestamp() + sleep_seconds)
            print(f"[NEXT CYCLE] Triggering in {interval_minutes} minutes at: {next_run_dt.strftime('%H:%M:%S')}")
            print("  (Press Ctrl+C at any time to stop)\n")

            await asyncio.sleep(sleep_seconds)

        except asyncio.CancelledError:
            print("\n[!] Autonomous agent stopping gracefully...")
            break
        except KeyboardInterrupt:
            print("\n[!] User stopped the autonomous loop.")
            break
        except Exception as exc:
            print(f"\n[!] Unexpected error in cycle: {exc}")
            print(f"  Auto-recovering in 60 seconds...")
            await asyncio.sleep(60)


def main():
    parser = argparse.ArgumentParser(description="Zohra 24/7 Autonomous News Research & Publisher")
    parser.add_argument(
        "--interval",
        type=int,
        default=10,
        help="Publishing interval in minutes (default: 10 minutes)",
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        help="Optional category filter (Technology, Science, Business, World Insights)",
    )
    parser.add_argument(
        "--mode",
        choices=["published", "draft"],
        default="published",
        help="Publishing status (published or draft, default: published)",
    )
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=None,
        help="Optional limit on number of articles to publish before stopping",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run only one autonomous cycle and exit",
    )

    args = parser.parse_args()
    max_c = 1 if args.once else args.max_cycles

    try:
        asyncio.run(
            autonomous_loop(
                interval_minutes=args.interval,
                category=args.category,
                mode=args.mode,
                max_cycles=max_c,
            )
        )
    except KeyboardInterrupt:
        print("\nShutdown complete.")


if __name__ == "__main__":
    main()
