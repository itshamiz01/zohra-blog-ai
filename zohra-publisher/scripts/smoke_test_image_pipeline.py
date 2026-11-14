"""
Controlled Live Smoke Test for Automatic Article Image Generation & Publishing.

Tests the full pipeline on a single test article:
Approved Article -> ArticleVisualAnalyzer -> ImageConceptGenerator ->
ArticleImagePromptBuilder -> ImageProviderRouter -> ImageArticleRelevanceValidator ->
ImageOptimizer -> PublicationGate -> GitStaticPublisher -> PostVerifier.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import get_settings
from app.media.analyzer import ArticleVisualAnalyzer
from app.media.concept import ImageConceptGenerator
from app.media.optimizer import ImageOptimizer
from app.media.prompt_builder import ArticleImagePromptBuilder
from app.media.providers.router import get_image_provider_router
from app.media.validator import ImageArticleRelevanceValidator
from app.publishing.gate import PublicationGate
from app.publishing.publishers.git_static import GitStaticPublisher
from app.publishing.seo import SchemaEngine, SEOPackager
from app.publishing.verifier import PostVerifier


async def run_smoke_test() -> None:
    settings = get_settings()
    print("=" * 70)
    print("ZOHRA ARTICLE IMAGE PIPELINE — CONTROLLED LIVE SMOKE TEST")
    print("=" * 70)
    print(f"Provider Configured: {settings.ARTICLE_IMAGE_PROVIDER}")
    print(f"Model: {settings.ARTICLE_IMAGE_MODEL} | Quality: {settings.ARTICLE_IMAGE_QUALITY}")
    print(f"Aspect Ratio: {settings.ARTICLE_IMAGE_ASPECT_RATIO}")
    print(f"Failure Policy: {settings.ARTICLE_IMAGE_FAILURE_POLICY}")
    print("-" * 70)

    # 1. Approved Test Article
    article_title = "How Students Can Use AI Without Becoming Dependent on It"
    article_topic = "AI in Education and Independent Study"
    article_category = "Education"
    article_sections = [
        {"title": "The Risk of Cognitive Offloading", "content": "Relying on AI can undermine deep conceptual understanding."},
        {"title": "AI as a Thought Partner", "content": "Using AI as an interactive Socratic tutor rather than an answer generator."},
        {"title": "Practical Daily Habits", "content": "Solving problems independently before checking AI feedback."},
    ]
    article_full_text = "Modern education is being transformed by generative AI. " * 8

    print(f"\n[1] APPROVED ARTICLE:")
    print(f"    Title: {article_title}")
    print(f"    Category: {article_category}")

    # 2. Visual Analysis
    print("\n[2] RUNNING ArticleVisualAnalyzer...")
    analysis = await ArticleVisualAnalyzer.analyze(
        title=article_title,
        topic=article_topic,
        category=article_category,
        sections=article_sections,
        full_text=article_full_text,
    )
    print(f"    Primary Subject: {analysis.primary_subject}")
    print(f"    Tone: {analysis.tone}")
    print(f"    Avoid Elements: {analysis.things_to_avoid[:3]}")

    # 3. Concept Generation
    print("\n[3] RUNNING ImageConceptGenerator...")
    concept = ImageConceptGenerator.generate_concept(analysis)
    print(f"    Image Type: {concept.image_type.value}")
    print(f"    Subject: {concept.subject}")
    print(f"    Visual Story: {concept.visual_story}")

    # 4. Prompt Generation
    print("\n[4] RUNNING ArticleImagePromptBuilder...")
    prompt_obj = ArticleImagePromptBuilder.build_prompt(concept)
    print(f"    Prompt Length: {len(prompt_obj.prompt_text)} characters")
    print(f"    Target Dims: {prompt_obj.target_width}x{prompt_obj.target_height}")
    assert "DO NOT include any text" in prompt_obj.prompt_text
    print("    Verified: No text requirement present in prompt.")

    # 5. Image Generation (Configured Provider)
    print("\n[5] CALLING ImageProviderRouter...")
    router = get_image_provider_router()
    provider = router.get_provider()
    print(f"    Using Provider: {provider.name}")
    raw_bytes, revised_prompt, cost = await provider.generate_image(prompt_obj)
    print(f"    Generated Image Size: {len(raw_bytes)} bytes | MIME: image/png")
    print(f"    Estimated Cost: ${cost:.4f}")

    # 6. Semantic & Quality Validation
    print("\n[6] RUNNING ImageArticleRelevanceValidator...")
    validation = await ImageArticleRelevanceValidator.validate(
        image_bytes=raw_bytes,
        analysis=analysis,
        concept=concept,
        prompt=prompt_obj,
    )
    print(f"    Relevance Score: {validation.score:.1f} / 100")
    print(f"    Passed: {validation.passed}")
    if not validation.passed:
        print(f"    Failure Reasons: {validation.failure_reasons}")
        raise RuntimeError("Image validation failed during smoke test.")

    # 7. Image Optimization & Derivatives
    print("\n[7] RUNNING ImageOptimizer...")
    opt_result = ImageOptimizer.optimize(
        raw_bytes=raw_bytes,
        title=article_title,
        analysis=analysis,
    )
    print(f"    Optimized Filename: {opt_result.filename}")
    print(f"    Optimized Dimensions: {opt_result.width}x{opt_result.height} ({opt_result.mime_type})")
    print(f"    File Size: {opt_result.file_size_bytes} bytes")
    print(f"    Content Hash (SHA-256): {opt_result.content_hash[:16]}...")
    print(f"    Alt Text: '{opt_result.alt_text}'")
    print(f"    Responsive Variants: {len(opt_result.responsive_variants)} variants generated")
    for v in opt_result.responsive_variants:
        print(f"      - {v.label}: {v.width}x{v.height} ({v.file_size_bytes} bytes)")

    # 8. Publication Gate Validation
    print("\n[8] RUNNING PublicationGate.validate_media_gate...")
    publication_payload = {
        "title": article_title,
        "slug": "how-students-can-use-ai-without-becoming-dependent",
        "rendered_html": f"<h1>{article_title}</h1><p>{article_full_text}</p>",
        "featured_image_bytes": opt_result.primary_bytes,
        "featured_image_filename": opt_result.filename,
        "featured_image_alt": opt_result.alt_text,
        "featured_image_caption": opt_result.caption,
        "featured_image_width": opt_result.width,
        "featured_image_height": opt_result.height,
        "featured_image_hash": opt_result.content_hash,
        "media_status": "READY",
        "media_validation_passed": True,
        "media_source_type": "AI_GENERATED" if getattr(provider, "is_generative_ai", True) else "PROCEDURAL",
        "media_provider": provider.name,
        "alt_text": opt_result.alt_text,
    }
    PublicationGate.validate_media_gate(publication_payload)
    print("    Publication Gate: PASS (all media prerequisites verified)")


    # 9. Staging / GitStatic Publisher
    print("\n[9] PUBLISHING TO STAGING VIA GitStaticPublisher...")
    staging_content_dir = project_root / "storage" / "staging_content"
    staging_assets_dir = project_root / "storage" / "staging_assets"
    publisher = GitStaticPublisher(root_dir=staging_content_dir)
    publisher.assets_dir = staging_assets_dir

    pub_result = await publisher.publish_article(
        prepared_payload=publication_payload,
        site_data={"domain": "zohra.ai"},
    )
    print(f"    Published Status: {pub_result['status']}")
    print(f"    Markdown Path: {pub_result['file_path']}")
    print(f"    Featured Image URL: {pub_result['featured_image']}")

    # 10. Post-Publish Verification
    print("\n[10] RUNNING PostVerifier...")
    saved_md = Path(pub_result["file_path"]).read_text(encoding="utf-8")
    assert f'featured_image: "/images/articles/{opt_result.filename}"' in saved_md
    assert f'featured_image_alt: "{opt_result.alt_text}"' in saved_md
    assert (staging_assets_dir / opt_result.filename).exists()

    seo_pkg = SEOPackager.build_seo_package(
        title=article_title,
        meta_description=f"Guide on {article_topic}",
        base_url="https://zohra.ai",
        featured_image_url=f"https://zohra.ai/images/articles/{opt_result.filename}",
    )
    schema_pkg = SchemaEngine.generate_article_schema(
        title=article_title,
        canonical_url="https://zohra.ai/articles/how-students-can-use-ai-without-becoming-dependent",
        published_at_iso="2026-10-03T12:00:00Z",
        featured_image_url=f"https://zohra.ai/images/articles/{opt_result.filename}",
    )

    post_mock = {
        "id": 1,
        "status": "published",
        "link": "https://zohra.ai/articles/how-students-can-use-ai-without-becoming-dependent",
        "title": {"rendered": article_title},
        "content": {"rendered": publication_payload["rendered_html"]},
        "featured_media": pub_result["featured_image"],
    }
    verif = PostVerifier.verify_post_and_media(
        post_data=post_mock,
        expected_title=article_title,
        expected_status="published",
        expected_media_id=pub_result["featured_image"],
        expected_alt_text=opt_result.alt_text,
        seo_package=seo_pkg,
        schema_package=schema_pkg,
    )
    print(f"    Post & Media Verification: PASS (media_verified={verif['media_verified']}, og_verified={verif['og_image_verified']})")

    print("\n" + "=" * 70)
    print("LIVE SMOKE TEST RESULT: SUCCESS")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_smoke_test())
