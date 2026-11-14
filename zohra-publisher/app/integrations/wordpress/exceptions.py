"""
Zohra — WordPress Integration Exceptions (Part 7).
"""

from __future__ import annotations

from app.core.exceptions import ZohraError


class WordPressError(ZohraError):
    """Base error for WordPress integration failures."""

    def __init__(self, message: str, code: str = "WORDPRESS_ERROR", status_code: int = 500):
        super().__init__(message, code=code)
        self.status_code = status_code


class WordPressAuthError(WordPressError):
    """Authentication or capability failure against WordPress REST API."""

    def __init__(self, message: str = "WordPress authentication failed"):
        super().__init__(message, code="WORDPRESS_AUTH_FAILED", status_code=401)


class WordPressConnectionError(WordPressError):
    """Network connection or unreachable WordPress host."""

    def __init__(self, message: str = "Failed to connect to WordPress REST API"):
        super().__init__(message, code="WORDPRESS_CONNECTION_FAILED", status_code=503)


class WordPressRateLimitError(WordPressError):
    """WordPress host responded with HTTP 429 Too Many Requests."""

    def __init__(self, message: str = "WordPress rate limit exceeded"):
        super().__init__(message, code="WORDPRESS_RATE_LIMITED", status_code=429)


class WordPressPostCreationError(WordPressError):
    """Post creation or update failed."""

    def __init__(self, message: str = "Failed to create WordPress post", status_code: int = 400):
        super().__init__(message, code="WORDPRESS_POST_CREATION_FAILED", status_code=status_code)


class WordPressMediaUploadError(WordPressError):
    """Media upload or attachment failed."""

    def __init__(self, message: str = "Failed to upload media to WordPress", status_code: int = 400):
        super().__init__(message, code="WORDPRESS_MEDIA_UPLOAD_FAILED", status_code=status_code)


class WordPressCircuitBreakerOpenError(WordPressError):
    """Circuit breaker is open due to consecutive site failures."""

    def __init__(self, site_id: str):
        super().__init__(
            f"WordPress publication circuit breaker open for site {site_id}",
            code="WORDPRESS_CIRCUIT_OPEN",
            status_code=503,
        )
