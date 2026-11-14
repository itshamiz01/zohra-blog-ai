"""
Zohra — Reddit Response Approval Queue.

Enforces operator review gate before any response is scheduled or published.
Supports actions: Approve with Link, Approve without Link, Edit, and Reject.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ZohraError
from app.core.logging import get_logger
from app.db.models.reddit import RedditJobStatus, RedditResponseDraft

logger = get_logger("reddit.approval")


class RedditApprovalManager:
    """Manages the human-in-the-loop review queue for Reddit response drafts."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_pending_drafts(self, site_id: uuid.UUID, limit: int = 50) -> list[RedditResponseDraft]:
        """Fetch all response drafts currently awaiting operator approval."""
        stmt = select(RedditResponseDraft).where(
            RedditResponseDraft.site_id == site_id,
            RedditResponseDraft.status.in_([
                RedditJobStatus.AWAITING_APPROVAL.value,
                RedditJobStatus.RESPONSE_DRAFTED.value,
            ]),
        ).order_by(RedditResponseDraft.created_at.desc()).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def approve_draft(
        self,
        draft_id: uuid.UUID,
        reviewed_by: str = "operator",
        strip_link: bool = False,
        custom_body: str | None = None,
    ) -> RedditResponseDraft:
        """
        Approves a draft for submission, optionally stripping external link or modifying text.
        """
        stmt = select(RedditResponseDraft).where(RedditResponseDraft.id == draft_id)
        res = await self.db.execute(stmt)
        draft = res.scalar_one_or_none()
        if not draft:
            raise ZohraError(f"Reddit draft {draft_id} not found", code="DRAFT_NOT_FOUND")

        if custom_body:
            draft.response_body = custom_body.strip()

        if strip_link:
            draft.has_external_link = False
            draft.proposed_link = None
            draft.link_rationale = "Link removed by operator during approval."
            # Remove link portion from text if formatted with footer
            if "\n\n---\n\n*" in draft.response_body:
                draft.response_body = draft.response_body.split("\n\n---\n\n*")[0].strip()

        draft.status = RedditJobStatus.APPROVED.value
        draft.reviewed_by = reviewed_by
        draft.reviewed_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(draft)
        logger.info("Draft %s approved by %s (strip_link=%s)", draft_id, reviewed_by, strip_link)
        return draft

    async def reject_draft(
        self,
        draft_id: uuid.UUID,
        reason: str,
        reviewed_by: str = "operator",
    ) -> RedditResponseDraft:
        """Rejects a draft response."""
        stmt = select(RedditResponseDraft).where(RedditResponseDraft.id == draft_id)
        res = await self.db.execute(stmt)
        draft = res.scalar_one_or_none()
        if not draft:
            raise ZohraError(f"Reddit draft {draft_id} not found", code="DRAFT_NOT_FOUND")

        draft.status = RedditJobStatus.REJECTED.value
        draft.reviewed_by = reviewed_by
        draft.reviewed_at = datetime.utcnow()
        draft.rejection_reason = reason

        await self.db.flush()
        await self.db.refresh(draft)
        logger.info("Draft %s rejected by %s: %s", draft_id, reviewed_by, reason)
        return draft
