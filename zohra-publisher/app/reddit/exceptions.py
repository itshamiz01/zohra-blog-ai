"""
Zohra — Reddit Opportunity & Referral Engine Exceptions.
"""

from __future__ import annotations

from app.core.exceptions import ZohraError


class RedditError(ZohraError):
    """Base exception for Reddit Engine operations."""

    def __init__(self, message: str, code: str = "REDDIT_ERROR") -> None:
        super().__init__(message, code=code)


class RedditAuthError(RedditError):
    """Authentication or credential failure with Reddit API."""

    def __init__(self, message: str = "Reddit authentication failed") -> None:
        super().__init__(message, code="REDDIT_AUTH_FAILED")


class RedditRateLimitError(RedditError):
    """Reddit rate limit exceeded."""

    def __init__(self, message: str = "Reddit rate limit exceeded", retry_after_seconds: float = 60.0) -> None:
        super().__init__(message, code="REDDIT_RATE_LIMITED")
        self.retry_after_seconds = retry_after_seconds


class RedditUnavailableError(RedditError):
    """Reddit service is temporarily unavailable."""

    def __init__(self, message: str = "Reddit service unavailable") -> None:
        super().__init__(message, code="REDDIT_UNAVAILABLE")


class RedditPostNotFoundError(RedditError):
    """Target Reddit post was deleted, locked, or not found."""

    def __init__(self, message: str = "Reddit post not found or removed") -> None:
        super().__init__(message, code="REDDIT_POST_NOT_FOUND")


class RedditRuleViolationError(RedditError):
    """Action violates subreddit community rules or self-promotion policies."""

    def __init__(self, message: str = "Action violates subreddit community rules") -> None:
        super().__init__(message, code="REDDIT_RULE_VIOLATION")


class RedditSpamBlockedError(RedditError):
    """Action blocked by RedditAntiSpamGuard."""

    def __init__(self, message: str = "Action blocked by anti-spam guard") -> None:
        super().__init__(message, code="REDDIT_SPAM_BLOCKED")
