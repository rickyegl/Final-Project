from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path
from typing import Iterable, Optional

from .config import AppConfig
from .gemini_client import GeminiChatClient
from .prompting import BALDI_PERSONA_PROMPT
from .teacher_bot import TeacherBot
from .image_overlay import ImageOverlay


def run_cli(argv: Optional[Iterable[str]] = None) -> None:
    args = _parse_args(argv)
    config = _build_config(args)
    persona = _load_persona(args.persona)

    client = GeminiChatClient(config, system_instruction=persona)
    bot = TeacherBot(config, client)

    overlay = None
    if not args.no_overlay:
        try:
            overlay = _start_overlay(
                image_path=args.overlay_image,
                max_width=args.overlay_width,
                max_height=args.overlay_height,
                transparent=None if not args.overlay_opaque else False,
            )
        except Exception as exc:  # pragma: no cover - visual aid optional
            print(f"[Overlay disabled] {exc}", file=sys.stderr)

    try:
        if args.intro:
            baldi_intro = bot.ask(args.intro)
            _printf("Baldi", baldi_intro)

        _printf("System", "Type your question (or 'exit' to quit).")
        while True:
            try:
                user_text = input("You> ").strip()
            except (KeyboardInterrupt, EOFError):
                _printf("System", "Session ended.")
                break

            if not user_text:
                continue
            if user_text.lower() in {"exit", "quit"}:
                _printf("System", "Goodbye! Remember to practice your math facts!")
                break

            try:
                response = bot.ask(user_text)
            except Exception as exc:  # pragma: no cover - CLI path
                print(f"[Error] {exc}", file=sys.stderr)
                continue

            _printf("Baldi", response)
    finally:
        if overlay is not None:
            overlay.stop()


def _parse_args(argv: Optional[Iterable[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Command-line Baldi teacher chatbot powered by Gemini."
    )
    parser.add_argument(
        "--model",
        help="Gemini model to use (default: %(default)s)",
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
        help="Top-p nucleus sampling value for Gemini responses.",
        dest="top_p",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        help="Top-k sampling value for Gemini responses.",
        dest="top_k",
    )
    parser.add_argument(
        "--api-key",
        help="Override the Gemini API key (otherwise read from env).",
        dest="api_key",
    )
    parser.add_argument(
        "--persona",
        type=Path,
        help="Path to an alternate persona description.",
    )
    parser.add_argument(
        "--intro",
        help="Optional opening question Baldi should answer immediately.",
    )
    parser.add_argument(
        "--overlay-image",
        type=Path,
        default=Path("baldi.webp"),
        help="Path to the Baldi image to pin in the corner (default: ./baldi.webp).",
    )
    parser.add_argument(
        "--overlay-width",
        type=int,
        default=320,
        help="Maximum width for the overlay image in pixels (default: 320).",
    )
    parser.add_argument(
        "--overlay-height",
        type=int,
        default=320,
        help="Maximum height for the overlay image in pixels (default: 320).",
    )
    parser.add_argument(
        "--overlay-opaque",
        action="store_true",
        help="Force an opaque overlay background (transparency is on by default on Windows).",
    )
    parser.add_argument(
        "--no-overlay",
        action="store_true",
        help="Disable the Baldi overlay window.",
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


def _printf(speaker: str, message: str) -> None:
    for line in message.splitlines():
        if line:
            print(f"{speaker}> {line}")


def _start_overlay(
    *,
    image_path: Path,
    max_width: Optional[int],
    max_height: Optional[int],
    transparent: Optional[bool],
) -> Optional[ImageOverlay]:
    max_w = max_width if max_width and max_width > 0 else None
    max_h = max_height if max_height and max_height > 0 else None
    overlay = ImageOverlay(
        image_path=image_path,
        anchor="sw",
        padding=32,
        max_width=max_w,
        max_height=max_h,
        transparent=transparent,
    )
    overlay.start()
    return overlay
