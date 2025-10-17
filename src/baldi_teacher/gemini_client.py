from __future__ import annotations

from typing import Sequence

from .config import AppConfig
from .audio import get_audio_manager
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
        from google.ai import generativelanguage as glm

        genai.configure(api_key=config.api_key)
        self._model = genai.GenerativeModel(
            model_name=config.model,
            system_instruction=system_instruction,
            generation_config=genai.types.GenerationConfig(
                temperature=config.temperature,
                top_p=config.top_p,
                top_k=config.top_k,
            ),
            tools=[
                {
                    "function_declarations": [
                        {
                            "name": "play_great_job_sound",
                            "description": (
                                "Play Baldi's celebratory 'great job' sound to reward "
                                "correct answers."
                            ),
                            "parameters": {
                                "type": "object",
                                "properties": {},
                            },
                        },
                        {
                            "name": "play_wrong_sound",
                            "description": (
                                "Play Baldi's disappointed 'wrong answer' buzzer when a "
                                "student makes a mistake."
                            ),
                            "parameters": {
                                "type": "object",
                                "properties": {},
                            },
                        },
                        {
                            "name": "play_mad_sounds",
                            "description": (
                                "Play Baldi's comedic frustrated muttering when he wants "
                                "to emphasise a point."
                            ),
                            "parameters": {
                                "type": "object",
                                "properties": {},
                            },
                        },
                    ]
                }
            ],
            tool_config={
                "function_calling_config": {
                    "mode": "AUTO",
                }
            },
        )
        self._glm = glm
        self._audio_manager = get_audio_manager()

    def generate_reply(self, messages: Sequence[ChatMessage]) -> str:
        glm = self._glm
        contents = [message.as_gemini_content() for message in messages]
        while True:
            response = self._model.generate_content(contents, stream=False)
            if not response or not response.candidates:
                raise RuntimeError("No response from Gemini API.")

            candidate = response.candidates[0]
            parts = list(getattr(candidate.content, "parts", []))

            tool_calls = [
                part.function_call for part in parts if getattr(part, "function_call", None)
            ]
            text_fragments = [
                part.text for part in parts if getattr(part, "text", None)
            ]

            if tool_calls:
                if candidate.content:
                    contents.append(candidate.content)
                for call in tool_calls:
                    result = self._audio_manager.handle_function_call(call.name)
                    contents.append(
                        glm.Content(
                            role="user",
                            parts=[
                                glm.Part(
                                    function_response=glm.FunctionResponse(
                                        name=call.name,
                                        response=result,
                                    )
                                )
                            ],
                        )
                    )
                # Ask Gemini to continue now that the function response is appended.
                continue

            if text_fragments:
                return "".join(text_fragments).strip()

            finish_reason = getattr(candidate, "finish_reason", None)
            raise RuntimeError(
                f"Gemini response missing text and tool calls (finish_reason={finish_reason})."
            )
