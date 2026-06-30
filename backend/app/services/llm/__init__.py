from functools import lru_cache

from app.core.config import settings

from .anthropic import AnthropicProvider
from .base import LLMMessage, LLMProvider, LLMResponse
from .gemini import GeminiProvider

__all__ = ["LLMMessage", "LLMProvider", "LLMResponse", "get_llm_provider"]


@lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider:
    if settings.LLM_PROVIDER == "anthropic":
        return AnthropicProvider(
            api_key=settings.ANTHROPIC_API_KEY,
            model=settings.ANTHROPIC_MODEL,
        )
    return GeminiProvider(
        api_key=settings.GEMINI_API_KEY,
        model=settings.GEMINI_MODEL,
    )
