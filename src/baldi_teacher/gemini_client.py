from __future__ import annotations

from pathlib import Path
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

    def generate_reply(
        self,
        messages: Sequence[ChatMessage],
        *,
        attachments: Sequence[Path] = (),
    ) -> str:
        glm = self._glm
        contents = [message.as_gemini_content() for message in messages]
        if attachments:
            attachment_parts, attachment_labels = self._prepare_attachments(attachments)
            if attachment_parts:
                if contents and getattr(contents[-1], "role", None) == "user":
                    target_content = contents[-1]
                else:
                    # Ensure attachments live on a user turn so Gemini can attribute them.
                    target_content = glm.Content(role="user", parts=[])
                    contents.append(target_content)
                existing_parts = list(getattr(target_content, "parts", []))
                intro_text = "Bookshelf documents attached:\n" + "\n".join(
                    f"- {label}" for label in attachment_labels
                )
                existing_parts.append(glm.Part(text=intro_text))
                existing_parts.extend(attachment_parts)
                target_content.parts = existing_parts
        # Loop until Gemini returns plain text, replaying any required tool calls.
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
                            role="function",
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

    def _prepare_attachments(
        self,
        attachments: Sequence[Path],
    ) -> tuple[list[object], list[str]]:
        parts: list[object] = []
        labels: list[str] = []
        errors: list[str] = []
        for entry in attachments:
            try:
                part, label = self._build_attachment_part(Path(entry))
            except Exception as exc:
                errors.append(f"{entry}: {exc}")
                continue
            parts.append(part)
            labels.append(label)
        if errors:
            raise RuntimeError(
                "Unable to attach bookshelf files:\n" + "\n".join(f"- {msg}" for msg in errors)
            )
        return parts, labels

    def _build_attachment_part(
        self,
        path: Path,
    ) -> tuple[object, str]:
        glm = self._glm
        if not path.exists():
            raise FileNotFoundError("File does not exist.")
        suffix = path.suffix.lower()
        if suffix not in {".pdf", ".txt"}:
            raise ValueError(f"Unsupported file type '{path.suffix}'.")
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path

        if suffix == ".pdf":
            size = resolved.stat().st_size
            if size > 20 * 1024 * 1024:
                raise ValueError("PDF files larger than 20MB cannot be attached inline.")
            try:
                data = resolved.read_bytes()
            except OSError as exc:
                raise RuntimeError(f"Could not read PDF file: {exc}") from exc
            part = glm.Part(
                inline_data=glm.Blob(
                    mime_type="application/pdf",
                    data=data,
                )
            )
            label = f"{resolved.name} (PDF)"
            return part, label

        try:
            text_content = resolved.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Fall back to lossy decoding so partially corrupt files still attach.
            text_content = resolved.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            raise RuntimeError(f"Could not read text file: {exc}") from exc
        part = glm.Part(text=f"[Text document: {resolved.name}]\n{text_content}")
        label = f"{resolved.name} (Text)"
        return part, label
