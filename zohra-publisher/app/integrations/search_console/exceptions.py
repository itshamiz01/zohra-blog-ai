"""
Zohra — Search Console Integration Exceptions (Part 8).
"""

from __future__ import annotations

from app.core.exceptions import ZohraError


class SearchConsoleError(ZohraError):
    """Base error for Google Search Console integration failures."""

    def __init__(self, message: str, code: str = "GSC_ERROR", status_code: int = 500):
        super().__init__(message, code=code)
        self.status_code = status_code


class SearchConsoleAuthError(SearchConsoleError):
    """Authentication or OAuth token failure."""

    def __init__(self, message: str = "Search Console authentication failed"):
        super().__init__(message, code="GSC_AUTH_FAILED", status_code=401)


class SearchConsoleConnectionError(SearchConsoleError):
    """Network or unreachable Google API host."""

    def __init__(self, message: str = "Failed to connect to Search Console API"):
        super().__init__(message, code="GSC_CONNECTION_FAILED", status_code=503)


class SearchConsoleRateLimitError(SearchConsoleError):
    """Google API responded with HTTP 429 or quota exceeded."""

    def __init__(self, message: str = "Search Console API quota exceeded"):
        super().__init__(message, code="GSC_RATE_LIMITED", status_code=429)


class SearchConsolePropertyNotFoundError(SearchConsoleError):
    """Requested property not found or not accessible."""

    def __init__(self, property_uri: str = ""):
        super().__init__(
            f"Search Console property not found: {property_uri}",
            code="GSC_PROPERTY_NOT_FOUND",
            status_code=404,
        )


class SearchConsoleCircuitBreakerOpenError(SearchConsoleError):
    """Circuit breaker is open due to consecutive GSC API failures."""

    def __init__(self, property_uri: str = ""):
        super().__init__(
            f"Search Console circuit breaker open for property: {property_uri}",
            code="GSC_CIRCUIT_OPEN",
            status_code=503,
        )


class SearchConsoleDataError(SearchConsoleError):
    """Invalid or unexpected data returned from Search Console API."""

    def __init__(self, message: str = "Unexpected data from Search Console API"):
        super().__init__(message, code="GSC_DATA_ERROR", status_code=502)
