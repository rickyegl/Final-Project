from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Deque, Sequence

from .config import AppConfig
from .gemini_client import GeminiChatClient
from .types import ChatMessage


class TeacherBot:
    """Conversation orchestrator that keeps a bounded history."""

    def __init__(
        self,
        config: AppConfig,
        client: GeminiChatClient,
    ) -> None:
        self._config = config
        self._client = client
        self._history: Deque[ChatMessage] = deque(
            maxlen=config.max_turn_history * 2
        )  # user + model pairs

    def prime(self, message: str) -> str:
        """Start the conversation with a user prompt."""
        return self.ask(message)

    def ask(
        self,
        message: str,
        *,
        bookshelf_files: Sequence[Path] | None = None,
    ) -> str:
        self._append_user(message)
        reply = self._client.generate_reply(
            tuple(self._history),
            attachments=tuple(bookshelf_files) if bookshelf_files else (),
        )
        self._append_model(reply)
        return reply

    def _append_user(self, text: str) -> None:
        self._history.append(ChatMessage(role="user", text=text.strip()))

    def _append_model(self, text: str) -> None:
        self._history.append(ChatMessage(role="model", text=text.strip()))
