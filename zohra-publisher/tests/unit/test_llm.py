"""
Tests for LLM provider abstraction and mock provider.
"""

import pytest

from app.llm.base import LLMRequest, LLMResponse, MockLLMProvider
from app.llm.registry import get_default_provider, list_providers


class TestLLMAbstraction:
    """LLM provider abstraction tests."""

    @pytest.mark.asyncio
    async def test_mock_provider_generate(self):
        """MockProvider returns a normalized response."""
        provider = MockLLMProvider(default_response="Test output")
        request = LLMRequest(prompt="Hello")
        response = await provider.generate(request)

        assert isinstance(response, LLMResponse)
        assert response.content == "Test output"
        assert response.provider == "mock"
        assert response.input_tokens > 0
        assert response.output_tokens > 0
        assert response.estimated_cost == 0.0
        assert response.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_mock_provider_health(self):
        provider = MockLLMProvider()
        assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_mock_provider_tracks_calls(self):
        provider = MockLLMProvider()
        assert provider.call_count == 0
        await provider.generate(LLMRequest(prompt="test"))
        assert provider.call_count == 1
        await provider.generate(LLMRequest(prompt="test2"))
        assert provider.call_count == 2

    def test_llm_request_defaults(self):
        req = LLMRequest(prompt="hello")
        assert req.temperature == 0.7
        assert req.max_tokens == 4096
        assert req.system_prompt is None

    def test_default_provider_returns_mock(self):
        """When no real providers are configured, mock is returned."""
        provider = get_default_provider()
        assert provider.name == "mock"

    def test_list_providers_includes_mock(self):
        providers = list_providers()
        assert "mock" in providers
