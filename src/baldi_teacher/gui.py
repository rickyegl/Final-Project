from __future__ import annotations

import argparse
import threading
from dataclasses import replace
from pathlib import Path
from typing import Iterable, Optional

from .config import AppConfig
from .gemini_client import GeminiChatClient
from .prompting import BALDI_PERSONA_PROMPT
from .teacher_bot import TeacherBot
from .gui_view import BaldiTeacherView
from .audio import get_audio_manager, AudioManager
from .characters import get_default_character, CharacterConfig
from .character_selector import show_character_selector


READY_STATUS = "Ready for the next question."
WAITING_STATUS = "Baldi is waiting for your question."
THINKING_STATUS = "Baldi is thinking while he is thinking."
ERROR_STATUS = "Something went wrong. Try again?"


def run_gui(argv: Optional[Iterable[str]] = None) -> None:
    """Initialize and launch the GUI application with character selection and audio support."""
    args = _parse_args(argv)
    config = _build_config(args)

    # Initialize with default character (Baldi)
    current_character = get_default_character()
    persona = _load_persona(args.persona)

    # Initialize audio manager with character audio directory
    assets_root = Path(__file__).resolve().parents[2] / "assets"
    from .audio import _AUDIO_MANAGER, AudioManager
    if _AUDIO_MANAGER is None:
        # Create audio manager with character-specific audio directory
        import sys
        audio_manager = AudioManager(assets_root, current_character.audio_dir)
        sys.modules['baldi_teacher.audio']._AUDIO_MANAGER = audio_manager

    client = GeminiChatClient(config, system_instruction=persona)
    bot = TeacherBot(config, client)

    view = BaldiTeacherView(
        avatar_path=args.avatar_image,
        thinking_path=args.thinking_image,
    )
    controller = BaldiTeacherController(
        bot=bot,
        view=view,
        intro_question=args.intro,
        config=config,
        current_character=current_character,
    )
    controller.run()


def _parse_args(argv: Optional[Iterable[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Graphical Baldi teacher chatbot powered by Gemini."
    )
    parser.add_argument(
        "--model",
        help="Gemini model to use (default: from environment or config).",
        default=None,
    )
    parser.add_argument(
        "--history",
        type=int,
        help="Number of past turns to retain.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        help="Sampling temperature for Gemini responses.",
    )
    parser.add_argument(
        "--top-p",
        type=float,
        dest="top_p",
        help="Top-p nucleus sampling value.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        dest="top_k",
        help="Top-k sampling value.",
    )
    parser.add_argument(
        "--api-key",
        dest="api_key",
        help="Override the Gemini API key (otherwise read from env).",
    )
    parser.add_argument(
        "--persona",
        type=Path,
        help="Path to an alternate persona description.",
    )
    parser.add_argument(
        "--intro",
        help="Optional question Baldi should answer immediately on launch.",
    )
    parser.add_argument(
        "--avatar-image",
        type=Path,
        default=Path("assets/characters/baldi/character.webp"),
        help="Path to Baldi's avatar image displayed in the window.",
    )
    parser.add_argument(
        "--thinking-image",
        type=Path,
        default=Path("assets/characters/baldi/thinking.png"),
        help="Optional alternate image to show while Baldi is thinking.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def _build_config(args: argparse.Namespace) -> AppConfig:
    config = AppConfig.from_env(api_key=args.api_key)
    if args.model:
        config = replace(config, model=args.model)
    if args.history:
        if args.history <= 0:
            raise ValueError("--history must be positive.")
        config = replace(config, max_turn_history=args.history)
    if args.temperature is not None:
        config = replace(config, temperature=args.temperature)
    if args.top_p is not None:
        config = replace(config, top_p=args.top_p)
    if args.top_k is not None:
        config = replace(config, top_k=args.top_k)
    return config


def _load_persona(persona_path: Optional[Path]) -> str:
    if persona_path is None:
        return BALDI_PERSONA_PROMPT
    return persona_path.read_text(encoding="utf-8").strip()


class BaldiTeacherController:
    """Coordinates chat logic and delegates rendering to the view."""

    def __init__(
        self,
        *,
        bot: TeacherBot,
        view: BaldiTeacherView,
        intro_question: Optional[str],
        config: AppConfig,
        current_character: CharacterConfig,
    ) -> None:
        self._bot = bot
        self._view = view
        self._intro_question = intro_question
        self._is_pending = False
        self._closing = False
        self._audio = get_audio_manager()
        self._config = config
        self._current_character = current_character

    def run(self) -> None:
        """Start the GUI event loop and handle initial setup like intro question."""
        self._audio.play_event("app_start")
        self._view.set_on_send(self._handle_send)
        self._view.set_on_close(self._handle_close)
        self._view.set_on_character_select(self._handle_character_select)

        # Initialize view with the current character's name
        assets_root = Path(__file__).resolve().parents[2] / "assets"
        avatar_path = assets_root / self._current_character.avatar_path
        thinking_path = assets_root / self._current_character.thinking_path if self._current_character.thinking_path else None
        self._view.update_character(self._current_character.name, avatar_path, thinking_path)

        self._view.update_status(READY_STATUS)
        self._view.set_pending_state(False)

        if self._intro_question:
            self._submit_intro(self._intro_question)

        self._view.start()

    # Event handlers ------------------------------------------------------------
    def _handle_send(self, raw_text: str) -> bool:
        if self._closing or self._is_pending:
            return False

        text = raw_text.strip()
        if not text:
            self._view.update_status(WAITING_STATUS)
            return False

        self._view.show_user_message(text)
        self._start_async_request(text)
        return True

    def _handle_close(self) -> bool:
        if self._closing:
            return True
        self._closing = True
        self._audio.play_event("window_close", blocking=True)
        return True

    def _handle_character_select(self) -> None:
        """Open character selection dialog."""
        if self._is_pending:
            return  # Don't allow character switching during pending operations

        def on_select(character: CharacterConfig) -> None:
            self._switch_character(character)

        show_character_selector(
            self._view._root,
            on_select,
            self._current_character.id
        )

    def _switch_character(self, character: CharacterConfig) -> None:
        """Switch to a new character by updating audio, bot persona, and UI assets."""
        if character.id == self._current_character.id:
            return  # No change needed

        self._current_character = character

        # Update audio manager with new character audio directory
        assets_root = Path(__file__).resolve().parents[2] / "assets"
        global _AUDIO_MANAGER
        from .audio import _AUDIO_MANAGER
        self._audio = AudioManager(assets_root, character.audio_dir)
        # Update the global audio manager
        import sys
        sys.modules[__name__]._audio = self._audio

        # Create new bot with updated character persona
        client = GeminiChatClient(self._config, system_instruction=character.persona_prompt)
        self._bot = TeacherBot(self._config, client)

        # Update view with new character assets
        avatar_path = assets_root / character.avatar_path
        thinking_path = assets_root / character.thinking_path if character.thinking_path else None
        self._view.update_character(character.name, avatar_path, thinking_path)

        # Show system message about character change
        self._view.show_system_message(f"Switched to {character.name}! {character.description}")

    # Conversation orchestration ------------------------------------------------
    def _submit_intro(self, question: str) -> None:
        self._view.show_user_message(question)
        self._start_async_request(question)

    def _start_async_request(self, text: str) -> None:
        self._set_pending(True)
        bookshelf_files = self._view.get_bookshelf_files()
        threading.Thread(
            target=self._generate_reply,
            args=(text, bookshelf_files),
            daemon=True,
        ).start()

    def _generate_reply(self, text: str, bookshelf_files: tuple[Path, ...]) -> None:
        """Request AI response in background thread and handle success or error."""
        try:
            reply = self._bot.ask(text, bookshelf_files=bookshelf_files)
        except Exception as exc:
            self._view.run_on_ui_thread(lambda exc=exc: self._handle_error(exc))
            return
        self._view.run_on_ui_thread(lambda reply=reply: self._handle_reply(reply))

    def _handle_reply(self, reply: str) -> None:
        if self._closing:
            return
        self._view.show_baldi_message(reply)
        self._set_pending(False)

    def _handle_error(self, exc: Exception) -> None:
        if self._closing:
            return
        self._view.show_system_message(f"[Error] {exc}")
        self._set_pending(False, update_status=False)
        self._view.update_status(ERROR_STATUS)

    def _set_pending(self, pending: bool, *, update_status: bool = True) -> None:
        self._is_pending = pending
        self._view.set_pending_state(pending)
        if update_status:
            if pending:
                self._view.update_status(THINKING_STATUS)
            else:
                self._view.update_status(READY_STATUS)


__all__ = ["run_gui"]
