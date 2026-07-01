from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class LLMUnavailableError(Exception):
    """Raised when the LLM provider is temporarily unavailable (API error, rate limit, etc.)."""


@dataclass
class LLMMessage:
    role: str  # "user" | "assistant" | "system"
    content: str


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: dict = field(default_factory=dict)  # {"input_tokens": int, "output_tokens": int}


class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:
        ...

    @abstractmethod
    def model_name(self) -> str:
        ...
