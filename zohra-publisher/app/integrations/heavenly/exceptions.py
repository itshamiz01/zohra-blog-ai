"""
Zohra — Heavenly Insights Integration Exceptions.
"""

from __future__ import annotations

from app.core.exceptions import ZohraError


class HeavenlyError(ZohraError):
    """Base error for Heavenly Insights integration failures."""

    def __init__(self, message: str, code: str = "HEAVENLY_ERROR", status_code: int = 500):
        super().__init__(message, code=code)
        self.status_code = status_code


class HeavenlyAuthError(HeavenlyError):
    """Authentication or capability failure against Heavenly Insights API."""

    def __init__(self, message: str = "Heavenly Insights authentication failed. Verify HEAVENLY_API_TOKEN."):
        super().__init__(message, code="HEAVENLY_AUTH_FAILED", status_code=401)


class HeavenlyConnectionError(HeavenlyError):
    """Network connection or unreachable Heavenly Insights host."""

    def __init__(self, message: str = "Failed to connect to Heavenly Insights API"):
        super().__init__(message, code="HEAVENLY_CONNECTION_FAILED", status_code=503)


class HeavenlyRateLimitError(HeavenlyError):
    """Heavenly Insights host responded with HTTP 429 Too Many Requests."""

    def __init__(self, message: str = "Heavenly Insights rate limit exceeded"):
        super().__init__(message, code="HEAVENLY_RATE_LIMITED", status_code=429)


class HeavenlyPostError(HeavenlyError):
    """Post creation or update failed on Heavenly Insights API."""

    def __init__(self, message: str = "Failed to create or update Heavenly Insights post", status_code: int = 400):
        super().__init__(message, code="HEAVENLY_POST_FAILED", status_code=status_code)


class HeavenlyValidationError(HeavenlyError):
    """Validation failure for article payload."""

    def __init__(self, message: str = "Invalid article payload for Heavenly Insights"):
        super().__init__(message, code="HEAVENLY_VALIDATION_ERROR", status_code=422)


class HeavenlyImageUploadError(HeavenlyError):
    """Featured/cover image upload to Heavenly Insights failed."""

    def __init__(self, message: str = "Failed to upload image to Heavenly Insights", status_code: int = 502):
        super().__init__(message, code="HEAVENLY_IMAGE_UPLOAD_FAILED", status_code=status_code)
