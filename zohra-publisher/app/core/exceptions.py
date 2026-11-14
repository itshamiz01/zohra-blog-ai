"""
Zohra — Custom exception hierarchy.

Every custom exception inherits from ZohraError so upstream handlers
can catch the entire family.  FastAPI exception handlers in main.py
convert these into safe API responses — no stack traces, no secrets.
"""

from __future__ import annotations


class ZohraError(Exception):
    """Base for all Zohra application errors."""

    def __init__(self, message: str = "An unexpected error occurred", code: str = "INTERNAL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


# ── Configuration ────────────────────────────────────────────────


class ConfigurationError(ZohraError):
    def __init__(self, message: str = "Configuration error"):
        super().__init__(message, code="CONFIGURATION_ERROR")


# ── Database ─────────────────────────────────────────────────────


class DatabaseError(ZohraError):
    def __init__(self, message: str = "Database error"):
        super().__init__(message, code="DATABASE_ERROR")


# ── External Services ────────────────────────────────────────────


class ExternalServiceError(ZohraError):
    def __init__(self, message: str = "External service error", service: str = "unknown"):
        self.service = service
        super().__init__(message, code="EXTERNAL_SERVICE_ERROR")


# ── Authentication / Authorization ───────────────────────────────


class AuthenticationError(ZohraError):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, code="AUTHENTICATION_ERROR")


class AuthorizationError(ZohraError):
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, code="AUTHORIZATION_ERROR")


# ── Validation ───────────────────────────────────────────────────


class ValidationError(ZohraError):
    def __init__(self, message: str = "Validation error"):
        super().__init__(message, code="VALIDATION_ERROR")


# ── Budget ───────────────────────────────────────────────────────


class BudgetExceededError(ZohraError):
    def __init__(self, message: str = "AI budget limit exceeded"):
        super().__init__(message, code="BUDGET_EXCEEDED")


# ── Rate Limit ───────────────────────────────────────────────────


class RateLimitError(ZohraError):
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, code="RATE_LIMIT_EXCEEDED")


# ── Workflow ─────────────────────────────────────────────────────


class WorkflowError(ZohraError):
    def __init__(self, message: str = "Invalid workflow transition"):
        super().__init__(message, code="WORKFLOW_ERROR")


# ── Agent Execution ──────────────────────────────────────────────


class AgentExecutionError(ZohraError):
    def __init__(self, message: str = "Agent execution failed"):
        super().__init__(message, code="AGENT_EXECUTION_ERROR")


# ── Duplicate Operations ─────────────────────────────────────────


class DuplicateOperationError(ZohraError):
    def __init__(self, message: str = "Duplicate operation detected"):
        super().__init__(message, code="DUPLICATE_OPERATION")


# ── Feature Disabled ─────────────────────────────────────────────


class FeatureDisabledError(ZohraError):
    def __init__(self, feature: str = "unknown"):
        super().__init__(
            message=f"Feature '{feature}' is currently disabled",
            code="FEATURE_DISABLED",
        )
        self.feature = feature


# ── Autonomy Disabled ────────────────────────────────────────────


class AutonomyDisabledError(ZohraError):
    def __init__(self, message: str = "Autonomous operations are currently disabled"):
        super().__init__(message, code="AUTONOMY_DISABLED")
