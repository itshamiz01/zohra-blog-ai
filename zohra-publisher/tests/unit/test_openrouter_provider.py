"""
Unit tests for OpenRouter LLM Provider.
Verifies configuration, routing, resilience, cost estimation, and registry integration.
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.core.exceptions import ZohraError
from app.llm.base import LLMRequest, LLMRole, ProviderStatus
from app.llm.openrouter import OpenRouterLLMProvider
from app.llm.registry import get_default_provider, get_provider, reset_providers


class TestOpenRouterLLMProvider:

    def setup_method(self):
        reset_providers()

    def test_provider_initialization_unconfigured(self):
        provider = OpenRouterLLMProvider(api_key="")
        assert not provider.is_configured
        assert provider.status == ProviderStatus.UNAVAILABLE

    def test_provider_initialization_configured(self):
        provider = OpenRouterLLMProvider(api_key="sk-or-v1-testkey123")
        assert provider.is_configured
        assert provider.status == ProviderStatus.AVAILABLE
        assert "sk-or-v1-testkey123" not in repr(provider)

    def test_role_based_routing(self):
        provider = OpenRouterLLMProvider(api_key="sk-or-v1-testkey123")
        assert "openai" in provider.get_model_for_role(LLMRole.WRITING)
        assert "openai" in provider.get_model_for_role(LLMRole.BRAINSTORMING)
        assert "openai" in provider.get_model_for_role(LLMRole.RESEARCH)
        assert "openai" in provider.get_model_for_role(LLMRole.VERIFICATION)

    def test_cost_calculation(self):
        provider = OpenRouterLLMProvider(api_key="sk-or-v1-testkey123")
        # 1M input tokens + 1M output tokens for gpt-4o = 2.50 + 10.00 = 12.50
        cost = provider.calculate_cost("openai/gpt-4o", 1_000_000, 1_000_000)
        assert cost == 12.50

        # Free tier model
        free_cost = provider.calculate_cost("meta-llama/llama-3.1-8b-instruct:free", 10_000, 5_000)
        assert free_cost == 0.0

    @pytest.mark.asyncio
    async def test_generate_requires_key(self):
        provider = OpenRouterLLMProvider(api_key="")
        req = LLMRequest(prompt="Hello", role=LLMRole.WRITING)
        with pytest.raises(ZohraError) as exc_info:
            await provider.generate(req)
        assert exc_info.value.code == "OPENROUTER_KEY_MISSING"

    @pytest.mark.asyncio
    async def test_successful_generate_mocked(self):
        provider = OpenRouterLLMProvider(api_key="sk-or-v1-testkey123")
        mock_choice = MagicMock()
        mock_choice.message.content = "Test OpenRouter article response"
        mock_choice.finish_reason = "stop"

        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 50
        mock_usage.completion_tokens = 100

        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        mock_completion.usage = mock_usage
        mock_completion.system_fingerprint = "fp_123"

        with patch.object(
            provider._client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_completion,
        ):
            req = LLMRequest(prompt="Write article", role=LLMRole.WRITING)
            response = await provider.generate(req)

            assert response.content == "Test OpenRouter article response"
            assert response.provider == "openrouter"
            assert "openai" in response.model
            assert response.input_tokens == 50
            assert response.output_tokens == 100
            assert response.estimated_cost > 0.0

    def test_registry_integration_when_primary(self):
        with patch("app.llm.registry.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                LLM_PRIMARY_PROVIDER="openrouter",
                OPENROUTER_API_KEY="sk-or-v1-test",
                OPENROUTER_ENABLED=True,
                OPENAI_API_KEY="",
                OPENAI_ENABLED=False,
                GEMINI_ENABLED=False,
                GEMINI_API_KEY="",
            )
            provider = get_default_provider()
            assert provider.name == "openrouter"
