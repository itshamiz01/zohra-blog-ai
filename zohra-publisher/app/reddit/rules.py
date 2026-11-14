"""
Zohra — Subreddit Community Rule Checker & Policy Engine.

Retrieves and analyzes official subreddit community rules.
Ensures Zohra never posts unauthorized promotional links or violates
community self-promotion guidelines.

Safety Principle:
If rules are unknown or ambiguous, defaults to strict NO_LINK policy.
"""

from __future__ import annotations

from datetime import datetime
import re
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.reddit import RedditCommunityPolicy
from app.reddit.provider import RedditProvider

logger = get_logger("reddit.rules")

# Rule parsing regex indicators
DISALLOWED_LINK_PATTERNS = [
    r"\bno (external )?links\b",
    r"\bno self[- ]promotion\b",
    r"\bself[- ]promotion (is )?prohibited\b",
    r"\bno blog(s)?\b",
    r"\bno commercial\b",
    r"\bno advertising\b",
    r"\bno affiliate\b",
    r"\bno spam\b",
    r"\bno linking to your own\b",
    r"\bno promotional content\b",
]

PERMITTED_PROMOTION_PATTERNS = [
    r"\bself[- ]promotion (allowed|permitted) in\b",
    r"\brelevant links (allowed|permitted)\b",
    r"\bdisclosure required\b",
    r"\b10% rule\b",
    r"\b9:1 rule\b",
    r"\bhelpful resources allowed\b",
]

DISCLOSURE_REQUIRED_PATTERNS = [
    r"\bmust disclose\b",
    r"\bdisclosure is required\b",
    r"\bstate your affiliation\b",
    r"\bdeclare conflicts\b",
]


class SubredditRuleChecker:
    """Evaluates community policies and gates Reddit responses."""

    def __init__(self, db: AsyncSession, provider: RedditProvider | None = None) -> None:
        self.db = db
        self.provider = provider or RedditProvider()

    async def get_or_refresh_policy(
        self,
        site_id: uuid.UUID,
        subreddit: str,
        force_refresh: bool = False,
    ) -> RedditCommunityPolicy:
        """
        Retrieves cached community policy or queries Reddit API to inspect fresh rules.
        """
        clean_sub = subreddit.strip().lstrip("r/").rstrip("/").lower()

        stmt = select(RedditCommunityPolicy).where(
            RedditCommunityPolicy.site_id == site_id,
            RedditCommunityPolicy.subreddit == clean_sub,
        )
        res = await self.db.execute(stmt)
        policy = res.scalar_one_or_none()

        if policy and not force_refresh:
            return policy

        # Query live Reddit API for official subreddit rules
        try:
            rules_data = await self.provider.get_community_rules(clean_sub)
            rules = rules_data.get("rules", [])
            rules_text_list = []
            for r in rules:
                short_name = r.get("short_name", "")
                desc = r.get("description", "")
                rules_text_list.append(f"{short_name}: {desc}")

            full_rules_text = "\n".join(rules_text_list).lower()

            # Analyze restrictions
            has_link_ban = any(re.search(pat, full_rules_text) for pat in DISALLOWED_LINK_PATTERNS)
            has_explicit_perm = any(re.search(pat, full_rules_text) for pat in PERMITTED_PROMOTION_PATTERNS)
            has_disclosure = any(re.search(pat, full_rules_text) for pat in DISCLOSURE_REQUIRED_PATTERNS)

            # Default safe stance: links forbidden unless explicitly permitted and not banned
            external_links_allowed = has_explicit_perm and not has_link_ban
            self_promotion_allowed = has_explicit_perm and not has_link_ban
            disclosure_required = True  # Always adhere to transparent disclosure

            if policy:
                policy.external_links_allowed = external_links_allowed
                policy.self_promotion_allowed = self_promotion_allowed
                policy.disclosure_required = disclosure_required
                policy.rules_text = full_rules_text
                policy.raw_rules_json = rules
                policy.rule_status = "verified"
                policy.confidence = 0.90
                policy.last_verified_at = datetime.utcnow()
            else:
                policy = RedditCommunityPolicy(
                    site_id=site_id,
                    subreddit=clean_sub,
                    posting_allowed=True,
                    commenting_allowed=True,
                    external_links_allowed=external_links_allowed,
                    self_promotion_allowed=self_promotion_allowed,
                    disclosure_required=disclosure_required,
                    rules_text=full_rules_text,
                    raw_rules_json=rules,
                    rule_status="verified",
                    confidence=0.90,
                    last_verified_at=datetime.utcnow(),
                )
                self.db.add(policy)

            await self.db.flush()
            await self.db.refresh(policy)
            return policy

        except Exception as exc:
            logger.warning("Could not fetch rules for r/%s: %s. Using strict safe defaults.", clean_sub, exc)
            if not policy:
                policy = RedditCommunityPolicy(
                    site_id=site_id,
                    subreddit=clean_sub,
                    posting_allowed=True,
                    commenting_allowed=True,
                    external_links_allowed=False,  # Strict safe fallback
                    self_promotion_allowed=False,
                    disclosure_required=True,
                    rules_text="Unable to verify live rules. Strict link restriction enforced.",
                    raw_rules_json=[],
                    rule_status="rule_status_unknown",
                    confidence=0.0,
                    last_verified_at=datetime.utcnow(),
                )
                self.db.add(policy)
                await self.db.flush()
                await self.db.refresh(policy)

            return policy

    def check_link_permitted(self, policy: RedditCommunityPolicy) -> tuple[bool, str]:
        """
        Determines whether a contextual website link is allowed in this subreddit.
        """
        if policy.rule_status == "rule_status_unknown":
            return False, "Community rules are unconfirmed; external linking blocked for safety."

        if not policy.external_links_allowed or not policy.self_promotion_allowed:
            return False, f"Subreddit r/{policy.subreddit} strictly restricts self-promotional external links."

        return True, f"Subreddit r/{policy.subreddit} permits helpful contextual resources with disclosure."
