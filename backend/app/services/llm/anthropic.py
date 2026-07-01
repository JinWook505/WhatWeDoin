import anthropic as anthropic_sdk

from .base import LLMMessage, LLMProvider, LLMResponse, LLMUnavailableError


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001"):
        self._client = anthropic_sdk.AsyncAnthropic(api_key=api_key)
        self._model = model

    def model_name(self) -> str:
        return self._model

    async def chat(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:
        system_parts = [m.content for m in messages if m.role == "system"]
        system = "\n".join(system_parts) if system_parts else anthropic_sdk.NOT_GIVEN

        converted = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role != "system"
        ]

        max_tokens = kwargs.get("max_tokens", 1024)
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                system=system,
                messages=converted,
            )
        except (
            anthropic_sdk.RateLimitError,
            anthropic_sdk.APIStatusError,
            anthropic_sdk.APIConnectionError,
            anthropic_sdk.APITimeoutError,
        ) as exc:
            raise LLMUnavailableError(str(exc)) from exc

        return LLMResponse(
            content=response.content[0].text,
            model=response.model,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        )
