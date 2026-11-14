"""
Zohra — Google Gemini LLM Provider (Optional / Fallback).

Integrates Google Gemini via the official REST API.
Disabled by default in favor of OpenAI as primary provider.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.exceptions import ZohraError
from app.core.logging import get_logger
from app.llm.base import LLMProvider, LLMRequest, LLMResponse, ProviderStatus

logger = get_logger("llm.gemini")

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


class GeminiLLMProvider(LLMProvider):
    """LLM Provider using Google Gemini REST API (Optional / Secondary)."""

    name = "gemini"

    def __init__(self, api_key: str | None = None, default_model: str = DEFAULT_GEMINI_MODEL):
        settings = get_settings()
        self.api_key = api_key or getattr(settings, "GEMINI_API_KEY", None) or ""
        self.default_model = default_model or getattr(settings, "DEFAULT_GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.enabled = bool(getattr(settings, "GEMINI_ENABLED", False))
        
        if not self.enabled:
            self.status = ProviderStatus.DISABLED
        elif not self.api_key:
            self.status = ProviderStatus.UNAVAILABLE
        else:
            self.status = ProviderStatus.AVAILABLE

    def __repr__(self) -> str:
        configured = bool(self.api_key)
        return f"<GeminiLLMProvider configured={configured} enabled={self.enabled} status={self.status.value}>"

    def __str__(self) -> str:
        return self.__repr__()

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generates a text completion using Gemini."""
        if not self.enabled:
            raise ZohraError("Gemini provider is disabled in configuration.", code="GEMINI_DISABLED")

        if not self.api_key:
            self.status = ProviderStatus.AUTH_FAILED
            raise ZohraError("GEMINI_API_KEY is not configured in .env", code="GEMINI_KEY_MISSING")

        model = request.model or self.default_model
        if model.startswith("models/"):
            model = model.replace("models/", "")

        url = f"{self.base_url}/models/{model}:generateContent?key={self.api_key}"

        # Build message payload
        user_text = request.prompt
        if request.system_prompt:
            user_text = f"System Instructions:\n{request.system_prompt}\n\nTask:\n{request.prompt}"

        payload: dict[str, Any] = {
            "contents": [
                {
                    "parts": [{"text": user_text}]
                }
            ],
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
            },
        }

        if request.response_format:
            payload["generationConfig"]["responseMimeType"] = "application/json"

        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, json=payload)
        except Exception as exc:
            self.status = ProviderStatus.UNAVAILABLE
            raise ZohraError(f"Gemini connection failed: {exc}", code="GEMINI_CONNECTION_ERROR") from exc

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        if resp.status_code != 200:
            err_msg = resp.text[:400]
            if resp.status_code == 429 or "RESOURCE_EXHAUSTED" in err_msg or "quota" in err_msg.lower():
                self.status = ProviderStatus.QUOTA_EXHAUSTED
                logger.error("Gemini quota exhausted: %s", err_msg)
                raise ZohraError(f"Gemini quota exhausted: {err_msg}", code="GEMINI_QUOTA_EXHAUSTED")

            logger.error("Gemini API error: HTTP %d - %s", resp.status_code, err_msg)
            raise ZohraError(f"Gemini API error (HTTP {resp.status_code}): {err_msg}", code="GEMINI_API_ERROR")

        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise ZohraError("Gemini returned no candidates in response", code="GEMINI_EMPTY_RESPONSE")

        content_parts = candidates[0].get("content", {}).get("parts", [])
        generated_text = "".join(part.get("text", "") for part in content_parts)

        usage = data.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount", 0)
        candidates_tokens = usage.get("candidatesTokenCount", 0)

        self.status = ProviderStatus.AVAILABLE

        return LLMResponse(
            content=generated_text,
            provider="gemini",
            model=model,
            input_tokens=prompt_tokens,
            output_tokens=candidates_tokens,
            latency_ms=latency_ms,
            estimated_cost=0.0,
            raw_metadata={"finish_reason": candidates[0].get("finishReason")},
        )

    async def health_check(self) -> bool:
        """Checks if Gemini API is enabled, configured, and reachable."""
        if not self.enabled:
            return False
        if not self.api_key:
            return False
        try:
            url = f"{self.base_url}/models?key={self.api_key}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
            if resp.status_code == 200:
                self.status = ProviderStatus.AVAILABLE
                return True
            if resp.status_code == 429:
                self.status = ProviderStatus.QUOTA_EXHAUSTED
            return False
        except Exception:
            self.status = ProviderStatus.UNAVAILABLE
            return False
