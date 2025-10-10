from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence


Role = Literal["user", "model"]


@dataclass
class ChatMessage:
    """Represents one turn in the conversation history."""

    role: Role
    text: str

    def as_gemini_content(self) -> dict:
        return {"role": self.role, "parts": [{"text": self.text}]}


MessageHistory = Sequence[ChatMessage]
