import asyncio
import google.generativeai as genai

from .base import LLMMessage, LLMProvider, LLMResponse


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gemini-3.1-flash-lite"):
        genai.configure(api_key=api_key)
        self._model = model

    def model_name(self) -> str:
        return self._model

    async def chat(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:
        system_parts = [m.content for m in messages if m.role == "system"]
        system_instruction = "\n".join(system_parts) if system_parts else None

        history = []
        last_user_content = ""
        for m in messages:
            if m.role == "system":
                continue
            gemini_role = "model" if m.role == "assistant" else "user"
            if m is messages[-1] and m.role == "user":
                last_user_content = m.content
            else:
                history.append({"role": gemini_role, "parts": [m.content]})

        genai_model = genai.GenerativeModel(
            model_name=self._model,
            system_instruction=system_instruction,
        )
        chat_session = genai_model.start_chat(history=history)

        response = await asyncio.to_thread(
            chat_session.send_message, last_user_content or messages[-1].content
        )

        usage = {}
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            usage = {
                "input_tokens": response.usage_metadata.prompt_token_count or 0,
                "output_tokens": response.usage_metadata.candidates_token_count or 0,
            }

        return LLMResponse(
            content=response.text,
            model=self._model,
            usage=usage,
        )
