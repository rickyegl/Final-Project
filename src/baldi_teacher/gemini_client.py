from __future__ import annotations

from typing import Sequence

from .config import AppConfig
from .types import ChatMessage

try:
    import google.generativeai as genai
except ImportError as exc:  # pragma: no cover - helps users diagnose missing deps
    raise RuntimeError(
        "google-generativeai is required. Install with 'pip install google-generativeai'."
    ) from exc


class GeminiChatClient:
    """Thin wrapper around the Gemini chat API."""

    def __init__(self, config: AppConfig, system_instruction: str) -> None:
        genai.configure(api_key=config.api_key)
        self._model = genai.GenerativeModel(
            model_name=config.model,
            system_instruction=system_instruction,
            generation_config=genai.types.GenerationConfig(
                temperature=config.temperature,
                top_p=config.top_p,
                top_k=config.top_k,
            ),
        )

    def generate_reply(self, messages: Sequence[ChatMessage]) -> str:
        contents = [message.as_gemini_content() for message in messages]
        response = self._model.generate_content(contents, stream=False)
        if not response:
            raise RuntimeError("No response from Gemini API.")

        text = getattr(response, "text", None)
        if not text:
            # Occurs if the response only has candidates with function calls.
            raise RuntimeError("Gemini response does not contain text output.")
        return text.strip()
