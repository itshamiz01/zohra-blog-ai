"""
Zohra — LLM Provider Registry and Router.

Supports dynamic provider registration, role-based model routing,
configurable primary provider selection (OpenAI primary, Gemini optional/disabled),
resilient fallback handling, and centralized provider status reporting.
"""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.llm.base import LLMProvider, LLMRole, MockLLMProvider, ProviderStatus

logger = get_logger(__name__, component="llm_registry")

_providers: dict[str, LLMProvider] = {}


def register_provider(provider: LLMProvider) -> None:
    """Register an LLM provider instance."""
    _providers[provider.name] = provider
    logger.info("Registered LLM provider: %s", provider.name)


def _has_credential(key: Any) -> bool:
    """Return True if key is a non-empty string and not a test mock."""
    return isinstance(key, str) and bool(key.strip())


def get_provider(name: str) -> LLMProvider:
    """Retrieve a registered provider by name."""
    if name not in _providers:
        # Lazy initialization for known providers
        settings = get_settings()
        if name == "openrouter" and _has_credential(getattr(settings, "OPENROUTER_API_KEY", None)):
            from app.llm.openrouter import OpenRouterLLMProvider
            prov = OpenRouterLLMProvider()
            register_provider(prov)
            return prov
        elif name == "openai" and _has_credential(getattr(settings, "OPENAI_API_KEY", None)):
            from app.llm.openai import OpenAILLMProvider
            prov = OpenAILLMProvider()
            register_provider(prov)
            return prov
        elif name == "gemini" and _has_credential(getattr(settings, "GEMINI_API_KEY", None)):
            from app.llm.gemini import GeminiLLMProvider
            prov = GeminiLLMProvider()
            register_provider(prov)
            return prov
        raise KeyError(f"No LLM provider registered with name '{name}'")
    return _providers[name]


def list_providers() -> list[str]:
    """List all registered provider names."""
    return list(_providers.keys())


def get_default_provider(role: str | LLMRole | None = None) -> LLMProvider:
    """
    Return the primary configured LLM provider (OpenRouter or OpenAI by default).
    If the primary provider is unavailable or unconfigured, falls back
    to secondary providers or mock provider in test/dev.
    """
    settings = get_settings()
    primary = getattr(settings, "LLM_PRIMARY_PROVIDER", "openai")
    if isinstance(primary, str):
        primary = primary.lower()
    else:
        primary = "openai"

    openrouter_key = getattr(settings, "OPENROUTER_API_KEY", None)
    openrouter_enabled = getattr(settings, "OPENROUTER_ENABLED", True) is not False
    openai_key = getattr(settings, "OPENAI_API_KEY", None)
    openai_enabled = getattr(settings, "OPENAI_ENABLED", True) is not False
    gemini_key = getattr(settings, "GEMINI_API_KEY", None)
    gemini_enabled = getattr(settings, "GEMINI_ENABLED", False) is True

    # 1. Try primary provider: OpenRouter
    if primary == "openrouter":
        if "openrouter" in _providers:
            return _providers["openrouter"]
        if _has_credential(openrouter_key) and openrouter_enabled:
            from app.llm.openrouter import OpenRouterLLMProvider
            prov = OpenRouterLLMProvider()
            register_provider(prov)
            return prov

    # 2. Try primary provider: OpenAI
    elif primary == "openai":
        if "openai" in _providers:
            return _providers["openai"]
        if _has_credential(openai_key) and openai_enabled:
            from app.llm.openai import OpenAILLMProvider
            prov = OpenAILLMProvider()
            register_provider(prov)
            return prov

    # 3. Try primary provider: Gemini (if configured as primary)
    elif primary == "gemini":
        if "gemini" in _providers:
            return _providers["gemini"]
        if gemini_enabled and _has_credential(gemini_key):
            from app.llm.gemini import GeminiLLMProvider
            prov = GeminiLLMProvider()
            register_provider(prov)
            return prov

    # 4. Fallback Providers
    # Check OpenRouter if not already tried
    if primary != "openrouter" and openrouter_enabled and _has_credential(openrouter_key):
        if "openrouter" in _providers:
            return _providers["openrouter"]
        from app.llm.openrouter import OpenRouterLLMProvider
        prov = OpenRouterLLMProvider()
        register_provider(prov)
        return prov

    # Check OpenAI if not already tried
    if primary != "openai" and openai_enabled and _has_credential(openai_key):
        if "openai" in _providers:
            return _providers["openai"]
        from app.llm.openai import OpenAILLMProvider
        prov = OpenAILLMProvider()
        register_provider(prov)
        return prov

    # Check Gemini only if explicitly enabled
    if primary != "gemini" and gemini_enabled and _has_credential(gemini_key):
        if "gemini" in _providers:
            return _providers["gemini"]
        from app.llm.gemini import GeminiLLMProvider
        prov = GeminiLLMProvider()
        register_provider(prov)
        return prov

    # 5. Check registered non-mock providers
    for name, p in _providers.items():
        if name != "mock" and p.status not in (ProviderStatus.DISABLED, ProviderStatus.AUTH_FAILED):
            return p

    # 6. Default Mock Provider (available in test/fallback environments)
    if "mock" in _providers:
        return _providers["mock"]

    mock_prov = MockLLMProvider()
    register_provider(mock_prov)
    return mock_prov


def get_provider_status() -> dict[str, Any]:
    """
    Returns non-secret status summary for all providers.
    Safe for public/admin status reporting.
    """
    settings = get_settings()
    primary = getattr(settings, "LLM_PRIMARY_PROVIDER", "openai").lower()

    openrouter_key_present = bool(getattr(settings, "OPENROUTER_API_KEY", None))
    openrouter_enabled = bool(getattr(settings, "OPENROUTER_ENABLED", True))
    openai_key_present = bool(getattr(settings, "OPENAI_API_KEY", None))
    gemini_key_present = bool(getattr(settings, "GEMINI_API_KEY", None))
    gemini_enabled = bool(getattr(settings, "GEMINI_ENABLED", False))
    openai_enabled = bool(getattr(settings, "OPENAI_ENABLED", True))

    openrouter_status = "unavailable"
    if "openrouter" in _providers:
        openrouter_status = _providers["openrouter"].status.value
    elif openrouter_key_present and openrouter_enabled:
        openrouter_status = "configured"

    openai_status = "unavailable"
    if "openai" in _providers:
        openai_status = _providers["openai"].status.value
    elif openai_key_present and openai_enabled:
        openai_status = "configured"

    gemini_status = "disabled"
    if not gemini_enabled:
        gemini_status = "disabled"
    elif "gemini" in _providers:
        gemini_status = _providers["gemini"].status.value
    elif gemini_key_present:
        gemini_status = "configured"

    return {
        "primary_provider": primary,
        "openrouter": {
            "configured": openrouter_key_present,
            "enabled": openrouter_enabled,
            "primary": primary == "openrouter",
            "status": openrouter_status,
            "writing_model": getattr(settings, "OPENROUTER_WRITING_MODEL", "openai/gpt-4o"),
            "research_model": getattr(settings, "OPENROUTER_RESEARCH_MODEL", "openai/gpt-4o-mini"),
            "verification_model": getattr(settings, "OPENROUTER_VERIFICATION_MODEL", "openai/gpt-4o-mini"),
        },
        "openai": {
            "configured": openai_key_present,
            "enabled": openai_enabled,
            "primary": primary == "openai",
            "status": openai_status,
            "writing_model": getattr(settings, "OPENAI_WRITING_MODEL", "gpt-4o"),
            "research_model": getattr(settings, "OPENAI_RESEARCH_MODEL", "gpt-4o-mini"),
            "verification_model": getattr(settings, "OPENAI_VERIFICATION_MODEL", "gpt-4o-mini"),
        },
        "gemini": {
            "configured": gemini_key_present,
            "enabled": gemini_enabled,
            "primary": primary == "gemini",
            "status": gemini_status,
            "default_model": getattr(settings, "DEFAULT_GEMINI_MODEL", "gemini-2.5-flash"),
        },
    }


def reset_providers() -> None:
    """Clear all registered providers (used for test isolation)."""
    _providers.clear()
    register_provider(MockLLMProvider())


# Initialize mock provider by default
register_provider(MockLLMProvider())
