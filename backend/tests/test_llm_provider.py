from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.llm.base import LLMMessage, LLMResponse


@pytest.fixture
def user_messages():
    return [
        LLMMessage(role="system", content="You are a helpful assistant."),
        LLMMessage(role="user", content="Hello"),
    ]


class TestGeminiProvider:
    @patch("app.services.llm.gemini.genai")
    async def test_chat_returns_response(self, mock_genai, user_messages):
        mock_response = MagicMock()
        mock_response.text = "Hi there!"
        mock_response.usage_metadata.prompt_token_count = 10
        mock_response.usage_metadata.candidates_token_count = 5

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        mock_genai.Client.return_value = mock_client

        from app.services.llm.gemini import GeminiProvider
        provider = GeminiProvider(api_key="fake-key", model="gemini-3.1-flash-lite")
        result = await provider.chat(user_messages)

        assert isinstance(result, LLMResponse)
        assert result.content == "Hi there!"
        assert result.model == "gemini-3.1-flash-lite"
        assert result.usage["input_tokens"] == 10
        assert result.usage["output_tokens"] == 5

    @patch("app.services.llm.gemini.genai")
    def test_model_name(self, mock_genai):
        from app.services.llm.gemini import GeminiProvider
        provider = GeminiProvider(api_key="fake-key", model="gemini-3.1-flash-lite")
        assert provider.model_name() == "gemini-3.1-flash-lite"


class TestAnthropicProvider:
    @patch("app.services.llm.anthropic.anthropic_sdk.AsyncAnthropic")
    async def test_chat_returns_response(self, mock_client_cls, user_messages):
        mock_content = MagicMock()
        mock_content.text = "Hello!"
        mock_resp = MagicMock()
        mock_resp.content = [mock_content]
        mock_resp.model = "claude-haiku-4-5-20251001"
        mock_resp.usage.input_tokens = 8
        mock_resp.usage.output_tokens = 3

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        from app.services.llm.anthropic import AnthropicProvider
        provider = AnthropicProvider(api_key="fake-key")
        result = await provider.chat(user_messages)

        assert isinstance(result, LLMResponse)
        assert result.content == "Hello!"
        assert result.usage["input_tokens"] == 8
        assert result.usage["output_tokens"] == 3

    @patch("app.services.llm.anthropic.anthropic_sdk.AsyncAnthropic")
    def test_model_name(self, mock_client_cls):
        from app.services.llm.anthropic import AnthropicProvider
        provider = AnthropicProvider(api_key="fake-key", model="claude-haiku-4-5-20251001")
        assert provider.model_name() == "claude-haiku-4-5-20251001"


class TestGetLlmProvider:
    def test_returns_gemini_by_default(self):
        from app.services.llm import get_llm_provider
        get_llm_provider.cache_clear()

        with patch("app.services.llm.settings") as mock_settings:
            mock_settings.LLM_PROVIDER = "gemini"
            mock_settings.GEMINI_API_KEY = "fake"
            mock_settings.GEMINI_MODEL = "gemini-3.1-flash-lite"
            with patch("app.services.llm.gemini.genai"):
                from app.services.llm.gemini import GeminiProvider
                provider = get_llm_provider()
                assert isinstance(provider, GeminiProvider)
        get_llm_provider.cache_clear()

    def test_returns_anthropic_when_configured(self):
        from app.services.llm import get_llm_provider
        get_llm_provider.cache_clear()

        with patch("app.services.llm.settings") as mock_settings:
            mock_settings.LLM_PROVIDER = "anthropic"
            mock_settings.ANTHROPIC_API_KEY = "fake"
            mock_settings.ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
            with patch("app.services.llm.anthropic.anthropic_sdk.AsyncAnthropic"):
                from app.services.llm.anthropic import AnthropicProvider
                provider = get_llm_provider()
                assert isinstance(provider, AnthropicProvider)
        get_llm_provider.cache_clear()
