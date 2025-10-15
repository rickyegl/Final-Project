from __future__ import annotations

import re
import tkinter as tk
from pathlib import Path
from tkinter import font as tkfont
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from typing import Callable, Optional

from PIL import Image, ImageTk


BOLD_PATTERN = re.compile(r"\*\*(.+?)\*\*")
MATH_BOLD_PATTERN = re.compile(r"\\mathbf\{([^{}]+)\}")
MATH_CMD_PATTERN = re.compile(r"\\([a-zA-Z]+)")


class BaldiGUITheme:
    """Encapsulates fonts and style configuration for the Baldi GUI."""

    def __init__(self) -> None:
        self._fonts: dict[str, tkfont.Font] = {}

    def apply(self, root: tk.Misc) -> ttk.Style:
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("Heading.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Status.TLabel", font=("Segoe UI", 10), foreground="#555555")
        style.configure("TButton", padding=(12, 6))
        return style

    def configure_text_widget(self, widget: ScrolledText) -> None:
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

        math_font = base_font.copy()
        math_font.configure(slant="italic")

        math_bold_font = math_font.copy()
        math_bold_font.configure(weight="bold")

        self._fonts.update(
            {
                "base": base_font,
                "bold": bold_font,
                "italic": italic_font,
                "heading": heading_font,
                "subheading": subheading_font,
                "small_heading": small_heading_font,
                "math": math_font,
                "math_bold": math_bold_font,
            }
        )

        widget.tag_configure("label_user", foreground="#0b5394", font=bold_font)
        widget.tag_configure("label_baldi", foreground="#783f04", font=bold_font)
        widget.tag_configure("label_system", foreground="#20124d", font=bold_font)

        widget.tag_configure("text_user", foreground="#134f5c", font=base_font)
        widget.tag_configure("text_baldi", foreground="#20124d", font=base_font)
        widget.tag_configure("text_system", foreground="#4c1130", font=base_font)

        widget.tag_configure("bold", font=bold_font)
        widget.tag_configure("italic", font=italic_font)
        widget.tag_configure("heading1", font=heading_font, spacing1=6, spacing3=6)
        widget.tag_configure("heading2", font=subheading_font, spacing1=6, spacing3=6)
        widget.tag_configure("heading3", font=small_heading_font, spacing1=4, spacing3=4)

        widget.tag_configure(
            "bullet",
            lmargin1=24,
            lmargin2=36,
            spacing1=2,
            spacing3=2,
        )
        widget.tag_configure(
            "separator",
            foreground="#b7b7b7",
            spacing1=6,
            spacing3=6,
        )

        widget.tag_configure("math", font=math_font, foreground="#0b5394")
        widget.tag_configure("math_bold", font=math_bold_font, foreground="#0b5394")
        widget.tag_configure(
            "math_block",
            font=math_font,
            foreground="#0b5394",
            justify="center",
            spacing1=6,
            spacing3=6,
        )


class BaldiTeacherView:
    """Tkinter view responsible for layout, styling, and rich text rendering."""

    def __init__(
        self,
        *,
        avatar_path: Path,
        thinking_path: Optional[Path],
        theme: Optional[BaldiGUITheme] = None,
    ) -> None:
        self._theme = theme or BaldiGUITheme()
        self._root = tk.Tk()
        self._root.title("Baldi's Notebook of Knowledge")
        self._root.geometry("960x640")

        self._style = self._theme.apply(self._root)

        self._status_var = tk.StringVar(value="Ready to learn!")
        self._is_pending = False
        self._on_send: Optional[Callable[[str], bool]] = None
        self._on_close: Optional[Callable[[], bool | None]] = None

        self._avatar_path = avatar_path
        self._thinking_path = thinking_path
        self._avatar_fallback_text = "Baldi\nis\nwatching!"

        self._conversation: ScrolledText
        self._input_box: tk.Text
        self._send_button: ttk.Button
        self._avatar_label: ttk.Label
        self._avatar_image_default: Optional[ImageTk.PhotoImage] = None
        self._avatar_image_thinking: Optional[ImageTk.PhotoImage] = None

        self._build_ui()
        self._root.protocol("WM_DELETE_WINDOW", self._handle_close_event)

    # Public API -----------------------------------------------------------------
    def set_on_send(self, callback: Callable[[str], bool]) -> None:
        self._on_send = callback

    def set_on_close(self, callback: Callable[[], bool | None]) -> None:
        self._on_close = callback

    def start(self) -> None:
        self._root.mainloop()

    def stop(self) -> None:
        self._root.quit()
        self._root.destroy()

    def run_on_ui_thread(self, func: Callable[[], None]) -> None:
        self._root.after(0, func)

    def update_status(self, text: str) -> None:
        self._status_var.set(text)

    def set_pending_state(self, pending: bool) -> None:
        self._is_pending = pending
        if pending:
            self._send_button.state(["disabled"])
        else:
            self._send_button.state(["!disabled"])
        self._update_avatar_state()

    def show_user_message(self, text: str) -> None:
        self._append_message("You", text, ("label_user", "text_user"))

    def show_baldi_message(self, text: str) -> None:
        self._append_message("Baldi", text, ("label_baldi", "text_baldi"))

    def show_system_message(self, text: str) -> None:
        self._append_message("System", text, ("label_system", "text_system"))

    # Internal helpers -----------------------------------------------------------
    def _build_ui(self) -> None:
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
        self._theme.configure_text_widget(self._conversation)

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
            command=self._handle_send_event,
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

    def _handle_send_event(self) -> None:
        if self._on_send is None:
            return
        text = self._input_box.get("1.0", "end")
        should_clear = self._on_send(text)
        if should_clear:
            self._input_box.delete("1.0", "end")
        self._input_box.focus_set()

    def _on_return_pressed(self, event: tk.Event) -> str:
        if event.state & 0x0001:  # Shift held
            return "break"
        self._handle_send_event()
        return "break"

    def _on_shift_return_pressed(self, event: tk.Event) -> None:
        self._input_box.insert("insert", "\n")

    def _handle_close_event(self) -> None:
        if self._on_close:
            keep_open = self._on_close()
            if keep_open is False:
                return
        self.stop()

    def _load_avatar(self, container: ttk.Frame) -> None:
        self._avatar_label = ttk.Label(container, anchor="center", justify="center")
        self._avatar_label.pack()

        self._avatar_image_default = self._create_photo_image(self._avatar_path)
        if self._thinking_path is not None:
            self._avatar_image_thinking = self._create_photo_image(self._thinking_path)
        self._update_avatar_state()

    def _append_message(self, speaker: str, text: str, tags: tuple[str, str]) -> None:
        label_tag, text_tag = tags
        self._conversation.configure(state="normal")
        self._conversation.insert("end", f"{speaker}> ", (label_tag,))
        self._insert_formatted_text(text, base_tag=text_tag)
        self._conversation.insert("end", "\n\n")
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

            if stripped.startswith("$$") and stripped.endswith("$$") and len(stripped) > 4:
                self._insert_math_block(stripped[2:-2].strip(), base_tag)
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
                self._insert_inline_markup(
                    bullet_content,
                    base_tag,
                    extra_tags=("bullet",),
                )
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
        for is_math, segment in self._split_math_segments(text):
            if not segment:
                continue
            if is_math:
                self._insert_math_inline(segment, base_tag, extra_tags)
            else:
                self._insert_bold_text(segment, base_tag, extra_tags)

    def _split_math_segments(self, text: str) -> list[tuple[bool, str]]:
        segments: list[tuple[bool, str]] = []
        buffer: list[str] = []
        i = 0
        length = len(text)
        while i < length:
            if text.startswith("$$", i):
                end = text.find("$$", i + 2)
                if end != -1:
                    if buffer:
                        segments.append((False, "".join(buffer)))
                        buffer.clear()
                    segments.append((True, text[i + 2 : end]))
                    i = end + 2
                    continue
            if text[i] == "$":
                end = text.find("$", i + 1)
                if end != -1:
                    if buffer:
                        segments.append((False, "".join(buffer)))
                        buffer.clear()
                    segments.append((True, text[i + 1 : end]))
                    i = end + 1
                    continue
            buffer.append(text[i])
            i += 1
        if buffer:
            segments.append((False, "".join(buffer)))
        return segments

    def _insert_bold_text(
        self,
        text: str,
        base_tag: str,
        extra_tags: tuple[str, ...],
    ) -> None:
        cursor = 0
        for match in BOLD_PATTERN.finditer(text):
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

    def _insert_math_inline(
        self,
        text: str,
        base_tag: str,
        extra_tags: tuple[str, ...],
    ) -> None:
        cursor = 0
        for match in MATH_BOLD_PATTERN.finditer(text):
            prefix = text[cursor:match.start()]
            if prefix:
                sanitized_prefix = self._sanitize_math_text(prefix)
                if sanitized_prefix:
                    self._conversation.insert(
                        "end",
                        sanitized_prefix,
                        (base_tag, "math") + extra_tags,
                    )
            bold_text = self._sanitize_math_text(match.group(1))
            if bold_text:
                self._conversation.insert(
                    "end",
                    bold_text,
                    (base_tag, "math", "math_bold") + extra_tags,
                )
            cursor = match.end()
        remainder = text[cursor:]
        if remainder:
            sanitized_remainder = self._sanitize_math_text(remainder)
            if sanitized_remainder:
                self._conversation.insert(
                    "end",
                    sanitized_remainder,
                    (base_tag, "math") + extra_tags,
                )

    def _insert_math_block(self, text: str, base_tag: str) -> None:
        if self._conversation.index("end-1c") != "1.0":
            try:
                previous_char = self._conversation.get("end-2c", "end-1c")
            except tk.TclError:
                previous_char = ""
            if previous_char and previous_char != "\n":
                self._conversation.insert("end", "\n")
        self._insert_math_inline(text, base_tag, ("math_block",))

    def _sanitize_math_text(self, text: str) -> str:
        cleaned = text.replace(r"\,", " ")
        cleaned = cleaned.replace(r"\ ", " ")
        cleaned = cleaned.replace(r"\-", "-")
        cleaned = MATH_CMD_PATTERN.sub(r"\1", cleaned)
        cleaned = cleaned.replace("{", "").replace("}", "")
        return cleaned

    def _update_avatar_state(self) -> None:
        if self._is_pending and self._avatar_image_thinking is not None:
            self._avatar_label.configure(
                image=self._avatar_image_thinking,
                text="",
                style="TLabel",
                padding=0,
            )
        elif self._avatar_image_default is not None:
            self._avatar_label.configure(
                image=self._avatar_image_default,
                text="",
                style="TLabel",
                padding=0,
            )
        elif self._avatar_image_thinking is not None:
            self._avatar_label.configure(
                image=self._avatar_image_thinking,
                text="",
                style="TLabel",
                padding=0,
            )
        else:
            self._avatar_label.configure(
                image="",
                text=self._avatar_fallback_text,
                style="Heading.TLabel",
                padding=8,
            )

    def _create_photo_image(self, path: Optional[Path]) -> Optional[ImageTk.PhotoImage]:
        if not path:
            return None
        try:
            image = Image.open(path)
            image.thumbnail((220, 220))
            return ImageTk.PhotoImage(image)
        except Exception:
            return None


__all__ = ["BaldiGUITheme", "BaldiTeacherView"]
