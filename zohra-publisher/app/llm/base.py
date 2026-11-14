"""
Zohra — LLM provider abstraction.

Defines provider-independent request/response objects and
an abstract provider interface so the system never hardcodes
a single AI vendor.

Part 1 includes only a MockProvider for testing.
Concrete providers (OpenAI, Gemini, Anthropic, Ollama)
will be added in later parts.
"""

from __future__ import annotations

import abc
from enum import Enum
import time
from typing import Any

from pydantic import BaseModel


class ProviderStatus(str, Enum):
    """Operational status of an LLM provider."""
    AVAILABLE = "available"
    DEGRADED = "degraded"
    RATE_LIMITED = "rate_limited"
    QUOTA_EXHAUSTED = "quota_exhausted"
    AUTH_FAILED = "auth_failed"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"


class LLMRole(str, Enum):
    """Logical task role for model routing."""
    WRITING = "writing"
    RESEARCH = "research"
    VERIFICATION = "verification"
    CLASSIFICATION = "classification"
    SUMMARIZATION = "summarization"
    BRAINSTORMING = "brainstorming"


# ── Normalized Data Objects ──────────────────────────────────────


class LLMRequest(BaseModel):
    """Provider-independent LLM request."""

    prompt: str
    system_prompt: str | None = None
    model: str | None = None
    role: str | LLMRole | None = None
    temperature: float = 0.7
    max_tokens: int = 4096
    response_format: Any | None = None  # Pydantic model class or dict schema for structured output
    metadata: dict[str, Any] = {}


class LLMResponse(BaseModel):
    """Provider-independent LLM response."""

    content: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    finish_reason: str | None = None
    latency_ms: float = 0.0
    estimated_cost: float = 0.0
    raw_metadata: dict[str, Any] = {}


# ── Abstract Provider ────────────────────────────────────────────


class LLMProvider(abc.ABC):
    """
    Abstract interface for LLM providers.
    Every provider must implement generate() and health_check().
    generate_structured() has a default implementation that parses
    the response through a Pydantic model.
    """

    name: str = "base"
    status: ProviderStatus = ProviderStatus.AVAILABLE

    def get_model_for_role(self, role: str | LLMRole | None) -> str:
        """Map a logical role to an actual model string for this provider."""
        return "default"

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate estimated cost in USD, or 0.0 if not known/free."""
        return 0.0

    @abc.abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a text response."""
        ...

    async def generate_structured(
        self,
        request: LLMRequest,
        response_model: type[BaseModel],
    ) -> tuple[BaseModel, LLMResponse]:
        """
        Generate and validate structured output.
        Returns (parsed_object, raw_response).
        Raises ValidationError if the LLM output doesn't match the schema.
        """
        response = await self.generate(request)
        # Parse the response content through the Pydantic model
        parsed = response_model.model_validate_json(response.content)
        return parsed, response

    @abc.abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider is reachable."""
        ...


# ── Mock Provider (for testing) ──────────────────────────────────


class MockLLMProvider(LLMProvider):
    """
    Test provider that returns deterministic responses.
    Never calls any external API.
    """

    name = "mock"

    def __init__(self, default_response: str = "Mock LLM response"):
        self.default_response = default_response
        self.call_count = 0

    async def generate(self, request: LLMRequest) -> LLMResponse:
        start = time.monotonic()
        self.call_count += 1
        elapsed = (time.monotonic() - start) * 1000

        return LLMResponse(
            content=self.default_response,
            provider="mock",
            model=request.model or "mock-model",
            input_tokens=len(request.prompt.split()),
            output_tokens=len(self.default_response.split()),
            finish_reason="stop",
            latency_ms=elapsed,
            estimated_cost=0.0,
        )

    async def health_check(self) -> bool:
        return True
