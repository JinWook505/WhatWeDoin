from google import genai
from google.genai import types
from google.genai import errors as genai_errors

from .base import LLMMessage, LLMProvider, LLMResponse, LLMUnavailableError


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gemini-3.1-flash-lite"):
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def model_name(self) -> str:
        return self._model

    async def chat(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:
        system_parts = [m.content for m in messages if m.role == "system"]
        system_instruction = "\n".join(system_parts) if system_parts else None

        contents = [
            types.Content(
                role="model" if m.role == "assistant" else "user",
                parts=[types.Part(text=m.content)],
            )
            for m in messages
            if m.role != "system"
        ]

        config = types.GenerateContentConfig(system_instruction=system_instruction)

        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=contents,
                config=config,
            )
        except genai_errors.APIError as exc:
            raise LLMUnavailableError(str(exc)) from exc

        usage = {}
        if response.usage_metadata:
            usage = {
                "input_tokens": response.usage_metadata.prompt_token_count or 0,
                "output_tokens": response.usage_metadata.candidates_token_count or 0,
            }

        return LLMResponse(
            content=response.text,
            model=self._model,
            usage=usage,
        )
