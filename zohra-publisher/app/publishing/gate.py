"""
Zohra — Publication Gate & Hash Authorization Validator (Part 7).

Verifies the cryptographic handoff from Part 6:
1. FinalAuditPackage decision == PASS
2. eligible_for_part7 == true
3. current_content_hash == audited_content_hash
4. audit_token signature validity
5. Publication authorization active and unexpired
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.audit.parser.content_parser import ContentParser
from app.audit.security.token import AuditTokenManager
from app.core.exceptions import ZohraError
from app.core.logging import get_logger

logger = get_logger("publishing.authorization.gate")


class PublicationGateError(ZohraError):
    """Raised when publication validation fails before any WordPress interaction."""

    def __init__(self, message: str, code: str = "PUBLICATION_GATE_FAILED"):
        super().__init__(message, code=code)


class PublicationGate:
    """Validates audit legitimacy and content immutability."""

    @classmethod
    def validate_audit_package(
        cls,
        final_audit_package_data: dict[str, Any],
        current_draft_text: str,
    ) -> bool:
        """
        Validates Part 6 decision, eligibility flag, cryptographic hash, and audit token.
        Raises PublicationGateError if any check fails.
        """
        decision = final_audit_package_data.get("decision")
        if decision != "PASS":
            raise PublicationGateError(
                f"Cannot publish unapproved content. Audit decision is {decision}",
                code="AUDIT_DECISION_NOT_PASS",
            )

        if not final_audit_package_data.get("eligible_for_part7", False):
            raise PublicationGateError(
                "Article is explicitly marked not eligible for Part 7 publication",
                code="INELIGIBLE_FOR_PUBLICATION",
            )

        # Hash validation
        audited_content_hash = final_audit_package_data.get("content_hash")
        current_content_hash = ContentParser.compute_content_hash(current_draft_text)

        if current_content_hash != audited_content_hash:
            logger.error(
                f"Content hash mismatch detected between audited draft ({audited_content_hash}) and current candidate ({current_content_hash})"
            )
            raise PublicationGateError(

                "Post-audit mutation detected: content has been altered since Part 6 approval. Re-audit required.",
                code="RE_AUDIT_REQUIRED",
            )

        # Audit token verification
        token = final_audit_package_data.get("audit_token")
        if not token:
            raise PublicationGateError(
                "Audit cryptographic token is missing",
                code="INVALID_AUDIT_TOKEN",
            )

        is_valid, msg = AuditTokenManager.verify_audit_token(token, audited_content_hash)
        if not is_valid:
            raise PublicationGateError(
                f"Invalid or mutated audit token: {msg}",
                code="INVALID_AUDIT_TOKEN",
            )

        return True


    @classmethod
    def validate_authorization_record(
        cls,
        authorization: Any,
        content_hash: str,
    ) -> bool:
        """Validates that a publication authorization record is ACTIVE and not expired."""
        if not authorization:
            raise PublicationGateError("Publication authorization record missing", code="AUTH_RECORD_MISSING")

        if authorization.status != "ACTIVE":
            raise PublicationGateError(
                f"Publication authorization is not active (status={authorization.status})",
                code="AUTH_NOT_ACTIVE",
            )

        now = datetime.now(UTC)
        if authorization.expires_at and authorization.expires_at < now:
            raise PublicationGateError("Publication authorization has expired", code="AUTH_EXPIRED")

        if authorization.content_hash != content_hash:
            raise PublicationGateError(
                "Authorization content hash does not match draft hash",
                code="AUTH_HASH_MISMATCH",
            )

        return True

    @classmethod
    def validate_media_gate(
        cls,
        prepared_payload: dict[str, Any],
        site_data: dict[str, Any] | None = None,
    ) -> bool:
        """
        Enforces media publication gates before article publication:
        - Checks if featured image is required.
        - Verifies that image exists, passed validation, has valid ALT text and path.
        - If generation failed and policy is BLOCK, raises PublicationGateError with code MEDIA_BLOCKED.
        """
        from app.core.config import get_settings

        settings = get_settings()
        site = site_data or {}

        images_enabled = getattr(settings, "ARTICLE_IMAGES_ENABLED", True)
        if not images_enabled:
            return True

        image_required = site.get("featured_image_required", getattr(settings, "ARTICLE_FEATURED_IMAGE_REQUIRED", True))
        failure_policy = getattr(settings, "ARTICLE_IMAGE_FAILURE_POLICY", "BLOCK").upper()

        has_image = bool(
            prepared_payload.get("featured_image_bytes")
            or prepared_payload.get("featured_image_url")
            or prepared_payload.get("featured_image")
        )
        media_status = prepared_payload.get("media_status", "READY")
        validation_passed = prepared_payload.get("media_validation_passed", True)

        if image_required:
            if not has_image or media_status in ("FAILED", "MEDIA_BLOCKED") or not validation_passed:
                logger.error(
                    f"Media gate failure: image_required={image_required}, has_image={has_image}, status={media_status}, validation_passed={validation_passed}"
                )
                if failure_policy == "BLOCK":
                    raise PublicationGateError(
                        "Featured image is required for this publication but media generation or validation failed.",
                        code="MEDIA_BLOCKED",
                    )

            # Validate alt text
            alt_text = (
                prepared_payload.get("featured_image_alt")
                or prepared_payload.get("alt_text")
                or ""
            ).strip()
            if not alt_text:
                if failure_policy == "BLOCK":
                    raise PublicationGateError(
                        "Featured image is present but lacks required accessible ALT text.",
                        code="MEDIA_BLOCKED",
                    )

            # Validate generative AI requirement: reject procedural placeholders if policy requires real generative AI
            require_generative = getattr(settings, "ARTICLE_IMAGE_REQUIRE_GENERATIVE_AI", True)
            allow_procedural = getattr(settings, "ARTICLE_IMAGE_ALLOW_PROCEDURAL_FALLBACK", False)
            source_type = (prepared_payload.get("source_type") or prepared_payload.get("media_source_type") or "").upper()
            provider = (prepared_payload.get("media_provider") or prepared_payload.get("provider") or "").lower()
            is_procedural = source_type == "PROCEDURAL" or provider == "procedural" or prepared_payload.get("is_procedural") is True

            if require_generative and is_procedural and not allow_procedural:
                logger.error("Media gate failure: Procedural placeholder rejected under generative-only policy.")
                if failure_policy == "BLOCK":
                    raise PublicationGateError(
                        "Procedural placeholder image is not permitted when generative AI is required.",
                        code="MEDIA_BLOCKED",
                    )

        return True

