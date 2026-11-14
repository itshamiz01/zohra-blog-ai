"""
Zohra — Article Image Service Orchestrator.

Coordinates the complete article media lifecycle:
UNDERSTAND ARTICLE → DESIGN VISUAL → GENERATE → VALIDATE → OPTIMIZE → ATTACH → PUBLISH → VERIFY.
"""

from __future__ import annotations

import datetime
import re
from typing import Any
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ZohraError
from app.core.logging import get_logger
from app.db.models.article_images import ArticleFeaturedMedia, ArticleImageBrandProfile
from app.db.models.draft_projects import DraftProject
from app.db.models.published_articles import PublishedArticle
from app.media.analyzer import ArticleVisualAnalyzer
from app.media.concept import ImageConceptGenerator
from app.media.models import BrandProfile, ImageGenerationStatus
from app.media.optimizer import ImageOptimizer
from app.media.prompt_builder import ArticleImagePromptBuilder
import app.media.providers.router as router_module
from app.media.validator import ImageArticleRelevanceValidator


logger = get_logger("media.service")


class ArticleImageService:
    """Master service for automatic article featured image generation and lifecycle management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_or_create_brand_profile(self, site_id: uuid.UUID | str) -> BrandProfile:
        """Retrieves site-specific brand profile or returns default."""
        sid = uuid.UUID(str(site_id))
        stmt = select(ArticleImageBrandProfile).where(ArticleImageBrandProfile.site_id == sid)
        res = await self.db.execute(stmt)
        record = res.scalar_one_or_none() if hasattr(res, "scalar_one_or_none") else None
        if hasattr(record, "__await__"):
            record = await record
        if record and hasattr(record, "site_id") and not callable(record.site_id):
            try:
                return BrandProfile(
                    site_id=str(record.site_id),
                    visual_style=getattr(record, "visual_style", "Modern clean editorial, authentic, balanced depth and natural light"),
                    preferred_composition=getattr(record, "preferred_composition", "Rule of thirds, clear focal subject, uncluttered background"),
                    preferred_mood=getattr(record, "preferred_mood", "Professional, intelligent, inviting, authentic"),
                    photography_preference=getattr(record, "photography_preference", 0.7),
                    illustration_preference=getattr(record, "illustration_preference", 0.3),
                    logo_policy=getattr(record, "logo_policy", "NO_LOGOS"),
                    text_overlay_policy=getattr(record, "text_overlay_policy", "NO_TEXT"),
                    aspect_ratio=getattr(record, "aspect_ratio", "16:9"),
                    quality=getattr(record, "quality", "standard"),
                )
            except Exception:
                pass
        return BrandProfile(site_id=str(sid))

    async def check_daily_budget(self, site_id: uuid.UUID | str) -> bool:
        """Enforces daily media generation budget limit."""
        settings = get_settings()
        daily_limit = getattr(settings, "ARTICLE_IMAGE_DAILY_BUDGET", 10.0)
        since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=24)
        sid = uuid.UUID(str(site_id))

        stmt = select(func.sum(ArticleFeaturedMedia.cost)).where(
            ArticleFeaturedMedia.site_id == sid,
            ArticleFeaturedMedia.created_at >= since,
        )
        res = await self.db.execute(stmt)
        cost_val = res.scalar() if hasattr(res, "scalar") else 0.0
        if hasattr(cost_val, "__await__"):
            cost_val = await cost_val
        try:
            total_cost = float(cost_val) if cost_val is not None else 0.0
        except (TypeError, ValueError):
            total_cost = 0.0

        if total_cost >= daily_limit:
            logger.warning(f"Daily image generation budget exhausted: spent ${total_cost:.2f} of ${daily_limit:.2f}")
            return False
        return True


    async def generate_featured_image(
        self,
        article_id: uuid.UUID | str,
        site_id: uuid.UUID | str,
        title: str,
        topic: str,
        category: str = "Technology",
        audience: str = "Learners and Practitioners",
        tone: str = "Authoritative and Practical",
        sections: list[dict[str, Any]] | None = None,
        full_text: str = "",
        publication_job_id: uuid.UUID | str | None = None,
        force_regenerate: bool = False,
    ) -> ArticleFeaturedMedia:
        """
        Executes complete automated generation, bounded validation/retry, optimization,
        and persistence for an article's featured hero image.
        """
        settings = get_settings()
        art_id = uuid.UUID(str(article_id))
        s_id = uuid.UUID(str(site_id))
        p_job_id = uuid.UUID(str(publication_job_id)) if publication_job_id else None

        # 1. Check feature flags
        if not settings.ARTICLE_IMAGES_ENABLED or not settings.ARTICLE_IMAGE_GENERATION_ENABLED:
            logger.info("Article image generation is disabled in settings.")
            raise ZohraError("Article image generation is disabled", code="MEDIA_GENERATION_DISABLED")

        # 2. Check Idempotency: avoid redundant generations for same article unless forced
        if not force_regenerate:
            existing_stmt = select(ArticleFeaturedMedia).where(
                ArticleFeaturedMedia.article_id == art_id,
                ArticleFeaturedMedia.is_active == True,
                ArticleFeaturedMedia.generation_status == ImageGenerationStatus.READY.value,
            )
            existing_res = await self.db.execute(existing_stmt)
            existing = existing_res.scalar_one_or_none()
            if hasattr(existing, "__await__"):
                existing = await existing
            if existing and getattr(existing, "public_url", None):
                logger.info(f"Reusing existing active featured image for article {art_id}: {existing.public_url}")
                return existing

        # 3. Budget enforcement
        if not await self.check_daily_budget(s_id):
            raise ZohraError("Daily image generation budget exhausted", code="IMAGE_BUDGET_EXHAUSTED")

        # 4. Visual Analysis & Concept
        brand = await self.get_or_create_brand_profile(s_id)
        analysis = await ArticleVisualAnalyzer.analyze(
            title=title,
            topic=topic,
            category=category,
            audience=audience,
            tone=tone,
            sections=sections,
            full_text=full_text,
            brand_identity=brand.visual_style,
        )
        concept = ImageConceptGenerator.generate_concept(analysis, brand)

        # 5. Generation & Bounded Validation Loop
        max_retries_raw = getattr(settings, "ARTICLE_IMAGE_MAX_REGENERATIONS", 2)
        try:
            max_retries = int(max_retries_raw)
        except Exception:
            max_retries = 2
        router = router_module.get_image_provider_router()
        provider = router.get_provider()


        retry_count = 0
        failure_feedback: str | None = None
        raw_bytes: bytes | None = None
        revised_prompt: str | None = None
        gen_cost: float = 0.0
        final_validation = None
        final_prompt_obj = None

        while retry_count <= max_retries:
            prompt_obj = ArticleImagePromptBuilder.build_prompt(
                concept=concept,
                brand=brand,
                retry_count=retry_count,
                failure_feedback=failure_feedback,
            )
            final_prompt_obj = prompt_obj

            logger.info(f"Attempting image generation attempt {retry_count + 1}/{max_retries + 1} for article {art_id}")
            try:
                raw_bytes, revised_prompt, cost = await provider.generate_image(prompt_obj)
                gen_cost += cost

                # Validate relevance & quality
                val_res = await ImageArticleRelevanceValidator.validate(
                    image_bytes=raw_bytes,
                    analysis=analysis,
                    concept=concept,
                    prompt=prompt_obj,
                    revised_prompt=revised_prompt,
                    brand=brand,
                )
                final_validation = val_res

                if val_res.passed:
                    logger.info(f"Image passed validation with score {val_res.score}")
                    break
                else:
                    logger.warning(
                        f"Image validation failed (score={val_res.score}, reasons={val_res.failure_reasons}). Retrying."
                    )
                    failure_feedback = val_res.suggested_prompt_fix
                    retry_count += 1

            except Exception as exc:
                logger.error(f"Image generation provider error (attempt {retry_count + 1}): {exc}")
                retry_count += 1
                if retry_count > max_retries:
                    if settings.ARTICLE_FEATURED_IMAGE_REQUIRED and settings.ARTICLE_IMAGE_FAILURE_POLICY == "BLOCK":
                        raise ZohraError(f"Featured image generation failed: {exc}", code="MEDIA_BLOCKED") from exc
                    raise

        if not raw_bytes or (final_validation and not final_validation.passed):
            if settings.ARTICLE_FEATURED_IMAGE_REQUIRED and settings.ARTICLE_IMAGE_FAILURE_POLICY == "BLOCK":
                raise ZohraError(
                    f"Featured image failed quality standards after {max_retries} attempts: {final_validation.failure_reasons if final_validation else 'unknown'}",
                    code="MEDIA_BLOCKED",
                )

        # 6. Optimization & WebP Encoding
        opt_res = ImageOptimizer.optimize(
            raw_bytes=raw_bytes,
            title=title,
            analysis=analysis,
            storage_subdir="media/articles",
        )

        # 7. Persist to Database
        media_record = ArticleFeaturedMedia(
            article_id=art_id,
            site_id=s_id,
            publication_job_id=p_job_id,
            provider=provider.name,
            model=getattr(settings, "ARTICLE_IMAGE_MODEL", "dall-e-3"),
            generation_status=ImageGenerationStatus.READY.value,
            prompt=final_prompt_obj.prompt_text if final_prompt_obj else "",
            revised_prompt=revised_prompt,
            visual_concept_json=concept.model_dump(),
            relevance_score=final_validation.score if final_validation else 85.0,
            validation_details_json=final_validation.model_dump() if final_validation else {},
            local_storage_path=opt_res.local_storage_path,
            public_url=opt_res.public_url,
            mime_type=opt_res.mime_type,
            width=opt_res.width,
            height=opt_res.height,
            file_size_bytes=opt_res.file_size_bytes,
            alt_text=opt_res.alt_text,
            caption=opt_res.caption,
            content_hash=opt_res.content_hash,
            perceptual_hash=opt_res.perceptual_hash,
            responsive_variants_json=[v.model_dump() for v in opt_res.responsive_variants],
            cost=gen_cost,
            provenance_metadata={
                "source_type": "AI_GENERATED",
                "provider": provider.name,
                "model": getattr(settings, "ARTICLE_IMAGE_MODEL", "dall-e-3"),
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            },
            is_approved=True,
            is_active=True,
        )
        self.db.add(media_record)
        await self.db.commit()
        await self.db.refresh(media_record)

        logger.info(f"Featured image ready and attached to article {art_id}: {media_record.public_url}")
        return media_record

    async def backfill_article_images(self, site_id: uuid.UUID | str, max_articles: int = 10) -> list[dict[str, Any]]:
        """
        Scans published articles missing featured images and generates them safely.
        Does NOT alter published URLs or slugs.
        """
        s_id = uuid.UUID(str(site_id))
        stmt = (
            select(PublishedArticle)
            .where(
                PublishedArticle.site_id == s_id,
                (PublishedArticle.featured_media_id == None),
            )
            .limit(max_articles)
        )
        res = await self.db.execute(stmt)
        articles = list(res.scalars().all())

        results = []
        for pub_art in articles:
            try:
                media = await self.generate_featured_image(
                    article_id=pub_art.article_id,
                    site_id=pub_art.site_id,
                    title=pub_art.title,
                    topic="Technology & Learning",
                    category="General",
                    publication_job_id=pub_art.publication_job_id,
                )
                results.append({
                    "article_id": str(pub_art.article_id),
                    "title": pub_art.title,
                    "status": "SUCCESS",
                    "image_url": media.public_url,
                })
            except Exception as e:
                results.append({
                    "article_id": str(pub_art.article_id),
                    "title": pub_art.title,
                    "status": "FAILED",
                    "error": str(e),
                })
        return results

    async def evaluate_article_image_on_update(
        self,
        article_id: uuid.UUID | str,
        new_title: str,
        new_topic: str,
        new_full_text: str = "",
    ) -> tuple[str, ArticleFeaturedMedia | None]:
        """
        Evaluates whether an updated article retains its existing featured image (KEEP)
        or has undergone material changes in meaning requiring new imagery (IMAGE_REFRESH_CANDIDATE).
        Section 47 / 48 compliance.
        """
        art_id = uuid.UUID(str(article_id))
        stmt = (
            select(ArticleFeaturedMedia)
            .where(
                ArticleFeaturedMedia.article_id == art_id,
                ArticleFeaturedMedia.is_active == True,
            )
            .order_by(ArticleFeaturedMedia.created_at.desc())
        )
        res = await self.db.execute(stmt)
        existing = res.scalar_one_or_none()
        if hasattr(existing, "__await__"):
            existing = await existing

        if not existing:
            return "NO_MEDIA", None

        # Manual editor overrides are protected
        if existing.is_approved and existing.generation_status == ImageGenerationStatus.READY.value:
            # Check if topic or title materially changed
            concept = existing.visual_concept_json or {}
            old_subject = concept.get("subject", "").lower()
            old_story = concept.get("visual_story", "").lower()

            new_title_words = set(re.sub(r"[^\w\s]", "", new_title.lower()).split())
            combined_old = old_subject + " " + old_story + " " + (existing.alt_text or "").lower()

            # Measure overlap
            matching_words = [w for w in new_title_words if len(w) > 3 and w in combined_old]
            overlap_ratio = len(matching_words) / max(len(new_title_words), 1)

            if overlap_ratio >= 0.35 or new_topic.lower() in combined_old:
                logger.info(f"Article update retains existing featured image (overlap={overlap_ratio:.2f}): KEEP")
                return "KEEP", existing

            # Material change in topic/subject
            logger.info(f"Article meaning changed materially (overlap={overlap_ratio:.2f}): IMAGE_REFRESH_CANDIDATE")
            existing.generation_status = "IMAGE_REFRESH_CANDIDATE"
            await self.db.commit()
            return "IMAGE_REFRESH_CANDIDATE", existing

        return "KEEP", existing

