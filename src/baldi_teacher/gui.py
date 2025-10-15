from __future__ import annotations

import argparse
import threading
import tkinter as tk
from dataclasses import replace
from pathlib import Path
from tkinter import ttk
from tkinter import font as tkfont
from tkinter.scrolledtext import ScrolledText
from typing import Iterable, Optional

from PIL import Image, ImageTk

from .config import AppConfig
from .gemini_client import GeminiChatClient
from .prompting import BALDI_PERSONA_PROMPT
from .teacher_bot import TeacherBot


def run_gui(argv: Optional[Iterable[str]] = None) -> None:
    args = _parse_args(argv)
    config = _build_config(args)
    persona = _load_persona(args.persona)

    client = GeminiChatClient(config, system_instruction=persona)
    bot = TeacherBot(config, client)

    app = _BaldiTeacherApp(
        bot=bot,
        avatar_path=args.avatar_image,
        intro_question=args.intro,
    )
    app.run()


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
        default=Path("baldi.webp"),
        help="Path to Baldi's avatar image displayed in the window.",
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


class _BaldiTeacherApp:
    """Tkinter GUI wrapper around the TeacherBot."""

    def __init__(
        self,
        *,
        bot: TeacherBot,
        avatar_path: Path,
        intro_question: Optional[str],
    ) -> None:
        self._bot = bot
        self._avatar_path = avatar_path
        self._intro_question = intro_question

        self._root = tk.Tk()
        self._root.title("Baldi's Notebook of Knowledge")
        self._root.geometry("960x640")

        self._status_var = tk.StringVar(value="Ready to learn!")
        self._is_pending = False

        self._conversation: ScrolledText
        self._input_box: tk.Text
        self._send_button: ttk.Button
        self._avatar_image: Optional[ImageTk.PhotoImage] = None

        self._build_ui()
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

    def run(self) -> None:
        if self._intro_question:
            self._queue_intro(self._intro_question)
        self._root.mainloop()

    def _build_ui(self) -> None:
        self._configure_style()

        main_pane = ttk.Frame(self._root, padding=16)
        main_pane.pack(fill="both", expand=True)

        header = ttk.Frame(main_pane)
        header.pack(fill="x", side="top")

        avatar_frame = ttk.Frame(header)
        avatar_frame.pack(side="left", anchor="n", padx=(0, 16))
        self._load_avatar(avatar_frame)

        title_label = ttk.Label(
            header,
            text="Baldi is ready to help!\nAsk anything, but write neatly!",
            style="Heading.TLabel",
            justify="left",
        )
        title_label.pack(side="left", anchor="n")

        conversation_frame = ttk.Frame(main_pane)
        conversation_frame.pack(fill="both", expand=True, pady=(16, 8))

        self._conversation = ScrolledText(
            conversation_frame,
            wrap="word",
            state="disabled",
            height=20,
            bg="#fffdf7",
            bd=0,
            highlightthickness=0,
            padx=12,
            pady=12,
        )
        self._conversation.pack(fill="both", expand=True)
        self._configure_text_tags()

        input_frame = ttk.Frame(main_pane)
        input_frame.pack(fill="x", side="bottom")

        self._input_box = tk.Text(
            input_frame,
            height=3,
            wrap="word",
        )
        self._input_box.pack(fill="x", side="left", expand=True, padx=(0, 12))
        self._input_box.bind("<Return>", self._on_return_pressed)
        self._input_box.bind("<Shift-Return>", self._on_shift_return_pressed)

        self._send_button = ttk.Button(
            input_frame,
            text="Send",
            command=self._on_send_clicked,
        )
        self._send_button.pack(side="right")

        status_bar = ttk.Label(
            main_pane,
            textvariable=self._status_var,
            style="Status.TLabel",
            anchor="w",
        )
        status_bar.pack(fill="x", side="bottom", pady=(8, 0))

        self._input_box.focus_set()

    def _configure_style(self) -> None:
        style = ttk.Style(self._root)
        style.theme_use("clam")
        style.configure("Heading.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Status.TLabel", font=("Segoe UI", 10), foreground="#555555")
        style.configure("TButton", padding=(12, 6))

    def _configure_text_tags(self) -> None:
        base_font = tkfont.nametofont("TkDefaultFont").copy()
        base_font.configure(size=12)

        bold_font = base_font.copy()
        bold_font.configure(weight="bold")

        italic_font = base_font.copy()
        italic_font.configure(slant="italic")

        heading_font = base_font.copy()
        heading_font.configure(size=15, weight="bold")

        subheading_font = base_font.copy()
        subheading_font.configure(size=13, weight="bold")

        small_heading_font = base_font.copy()
        small_heading_font.configure(size=12, weight="bold")

        self._conversation.tag_configure("label_user", foreground="#0b5394", font=bold_font)
        self._conversation.tag_configure("label_baldi", foreground="#783f04", font=bold_font)
        self._conversation.tag_configure("label_system", foreground="#20124d", font=bold_font)

        self._conversation.tag_configure("text_user", foreground="#134f5c", font=base_font)
        self._conversation.tag_configure("text_baldi", foreground="#20124d", font=base_font)
        self._conversation.tag_configure("text_system", foreground="#4c1130", font=base_font)

        self._conversation.tag_configure("bold", font=bold_font)
        self._conversation.tag_configure("italic", font=italic_font)
        self._conversation.tag_configure("heading1", font=heading_font, spacing1=6, spacing3=6)
        self._conversation.tag_configure("heading2", font=subheading_font, spacing1=6, spacing3=6)
        self._conversation.tag_configure("heading3", font=small_heading_font, spacing1=4, spacing3=4)

        self._conversation.tag_configure(
            "bullet",
            lmargin1=24,
            lmargin2=36,
            spacing1=2,
            spacing3=2,
        )
        self._conversation.tag_configure(
            "separator",
            foreground="#b7b7b7",
            spacing1=6,
            spacing3=6,
        )

    def _load_avatar(self, container: ttk.Frame) -> None:
        try:
            image = Image.open(self._avatar_path)
            image.thumbnail((220, 220))
            self._avatar_image = ImageTk.PhotoImage(image)
            label = ttk.Label(container, image=self._avatar_image)
            label.pack()
        except Exception:
            fallback = ttk.Label(
                container,
                text="Baldi\nis\nwatching!",
                style="Heading.TLabel",
                justify="center",
            )
            fallback.pack()

    def _on_return_pressed(self, event: tk.Event) -> str:
        if event.state & 0x0001:  # Shift held
            return "break"
        self._on_send_clicked()
        return "break"

    def _on_shift_return_pressed(self, event: tk.Event) -> None:
        self._input_box.insert("insert", "\n")

    def _on_send_clicked(self) -> None:
        if self._is_pending:
            return
        text = self._input_box.get("1.0", "end").strip()
        if not text:
            self._status_var.set("Baldi is waiting for your question.")
            return

        self._input_box.delete("1.0", "end")
        self._append_message("You", text, tags=("label_user", "text_user"))
        self._conversation.insert("end", "\n")
        self._conversation.see("end")

        self._set_pending(True)
        threading.Thread(target=self._dispatch_question, args=(text,), daemon=True).start()

    def _queue_intro(self, question: str) -> None:
        self._append_message("You", question, tags=("label_user", "text_user"))
        self._conversation.insert("end", "\n")
        self._conversation.see("end")
        self._set_pending(True)
        threading.Thread(target=self._dispatch_question, args=(question,), daemon=True).start()

    def _dispatch_question(self, text: str) -> None:
        try:
            reply = self._bot.ask(text)
        except Exception as exc:
            message = f"[Error] {exc}"
            self._root.after(
                0,
                lambda: self._append_message(
                    "System",
                    message,
                    tags=("label_system", "text_system"),
                ),
            )
            self._root.after(0, lambda: self._set_pending(False))
            return

        self._root.after(
            0,
            lambda: self._show_baldi_reply(reply),
        )

    def _show_baldi_reply(self, reply: str) -> None:
        self._append_message("Baldi", reply, tags=("label_baldi", "text_baldi"))
        self._conversation.insert("end", "\n")
        self._conversation.see("end")
        self._set_pending(False)

    def _set_pending(self, pending: bool) -> None:
        self._is_pending = pending
        if pending:
            self._status_var.set("Baldi is thinking... Don't forget to show your work!")
            self._send_button.state(["disabled"])
        else:
            self._status_var.set("Ready for the next question.")
            self._send_button.state(["!disabled"])

    def _append_message(self, speaker: str, text: str, *, tags: tuple[str, str]) -> None:
        label_tag, text_tag = tags
        self._conversation.configure(state="normal")
        self._conversation.insert("end", f"{speaker}> ", (label_tag,))
        self._insert_formatted_text(text, base_tag=text_tag)
        self._conversation.insert("end", "\n")
        self._conversation.configure(state="disabled")
        self._conversation.see("end")

    def _insert_formatted_text(self, text: str, *, base_tag: str) -> None:
        lines = text.splitlines()
        if not lines:
            return

        for index, line in enumerate(lines):
            stripped = line.strip()
            if stripped == "":
                self._conversation.insert("end", "\n")
                continue

            if stripped == "***":
                self._conversation.insert("end", "-" * 48, (base_tag, "separator"))
                self._conversation.insert("end", "\n")
                continue

            if stripped.startswith("### "):
                heading_tag = "heading3"
                content = line.split("### ", 1)[1].strip()
                self._conversation.insert("end", content, (base_tag, heading_tag))
            elif stripped.startswith("## "):
                heading_tag = "heading2"
                content = line.split("## ", 1)[1].strip()
                self._conversation.insert("end", content, (base_tag, heading_tag))
            elif stripped.startswith("# "):
                heading_tag = "heading1"
                content = line.split("# ", 1)[1].strip()
                self._conversation.insert("end", content, (base_tag, heading_tag))
            elif stripped.startswith(("- ", "* ")):
                bullet_content = stripped[2:].strip()
                self._conversation.insert("end", "- ", (base_tag, "bullet"))
                self._insert_inline_markup(bullet_content, base_tag, extra_tags=("bullet",))
            else:
                self._insert_inline_markup(line, base_tag)

            if index < len(lines) - 1:
                self._conversation.insert("end", "\n")

    def _insert_inline_markup(
        self,
        text: str,
        base_tag: str,
        extra_tags: tuple[str, ...] = (),
    ) -> None:
        import re

        bold_pattern = re.compile(r"\*\*(.+?)\*\*")

        cursor = 0
        for match in bold_pattern.finditer(text):
            prefix = text[cursor:match.start()]
            if prefix:
                self._conversation.insert(
                    "end",
                    prefix,
                    (base_tag,) + extra_tags,
                )
            bold_text = match.group(1)
            self._conversation.insert(
                "end",
                bold_text,
                (base_tag, "bold") + extra_tags,
            )
            cursor = match.end()

        remainder = text[cursor:]
        if remainder:
            self._conversation.insert(
                "end",
                remainder,
                (base_tag,) + extra_tags,
            )

    def _on_close(self) -> None:
        self._root.quit()
        self._root.destroy()


__all__ = ["run_gui"]
