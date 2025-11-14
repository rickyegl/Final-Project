from __future__ import annotations

import re
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, font as tkfont, messagebox
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from typing import Callable, Optional

from PIL import Image, ImageDraw, ImageFilter, ImageTk


BOLD_PATTERN = re.compile(r"\*(.+?)\*") # Look for single asterisks
# --- REMOVED ---
# The old math regex patterns are no longer needed,
# as we are not parsing the math content itself.
# MATH_BOLD_PATTERN = re.compile(r"\\mathbf\{([^{}]+)\}")
# MATH_CMD_PATTERN = re.compile(r"\\([a-zA-Z]+)")


class BaldiGUITheme:
    """Encapsulates fonts and style configuration for the Baldi GUI."""

    def __init__(self) -> None:
        self._fonts: dict[str, tkfont.Font] = {}

    def apply(self, root: tk.Misc) -> ttk.Style:
        style = ttk.Style(root)
        style.theme_use("clam")

        # Color scheme
        glass_surface = "#f8fafc"  # Light background
        glass_panel = "#ffffff"    # White panel
        text_primary = "#0f172a"   # Dark text
        text_muted = "#475569"     # Muted text
        accent = "#38bdf8"         # Blue accent
        border_color = "#e2e8f0"   # Light border

        # Configure base styles
        style.configure(".", background=glass_surface)
        style.configure("TLabel", background=glass_surface, foreground=text_primary)
        
        # Frame styles
        style.configure("GlassMain.TFrame", background=glass_surface)
        style.configure("GlassPanel.TFrame", 
            background=glass_panel,
            bordercolor=border_color
        )
        style.configure("GlassSurface.TFrame", background=glass_panel)
        style.configure(
            "Heading.TLabel",
            font=("Segoe UI", 18, "bold"),
            foreground=text_primary,
            background=glass_surface,
        )
        style.configure(
            "Status.TLabel",
            font=("Segoe UI", 10),
            foreground=text_muted,
            background=glass_surface,
            padding=(6, 4),
        )
        style.configure(
            "GlassAvatar.TLabel",
            background=glass_surface,
            foreground=text_primary,
            font=("Segoe UI", 12, "bold"),
        )
        style.configure(
            "GlassAccent.TButton",
            font=("Segoe UI", 11, "bold"),
            padding=(18, 10),
            borderwidth=0,
            background=accent,
            foreground="#f8fafc",
        )
        style.map(
            "GlassAccent.TButton",
            background=[("active", "#0ea5e9"), ("disabled", "#94a3b8")],
            foreground=[("disabled", "#e2e8f0")],
        )
        style.configure("TButton", padding=(16, 8), borderwidth=0, relief="flat")
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

        widget.configure(
            bg="#f9faff",
            fg="#0f172a",
            insertbackground="#0f172a",
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
        )

        widget.tag_configure("label_user", foreground="#0ea5e9", font=bold_font)
        widget.tag_configure("label_baldi", foreground="#a855f7", font=bold_font)
        widget.tag_configure("label_system", foreground="#ec4899", font=bold_font)

        widget.tag_configure("text_user", foreground="#0f172a", font=base_font)
        widget.tag_configure("text_baldi", foreground="#1e293b", font=base_font)
        widget.tag_configure("text_system", foreground="#be123c", font=base_font)

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
            foreground="#cbd5f5",
            spacing1=6,
            spacing3=6,
        )

        # This will just style the raw LaTeX text
        widget.tag_configure("math", font=math_font, foreground="#0284c7")
        # We leave math_bold in case you want to manually parse `\mathbf` later
        widget.tag_configure("math_bold", font=math_bold_font, foreground="#0284c7")
        widget.tag_configure(
            "math_block",
            font=math_font,
            foreground="#0284c7",
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
        self._root.minsize(640, 480)  # Set minimum window size
        self._root.configure(bg="#0f172a")

        self._style = self._theme.apply(self._root)

        self._status_var = tk.StringVar(value="Ready to learn!")
        self._is_pending = False
        self._on_send: Optional[Callable[[str], bool]] = None
        self._on_close: Optional[Callable[[], bool | None]] = None
        self._on_character_select: Optional[Callable[[], None]] = None

        self._avatar_path = avatar_path
        self._thinking_path = thinking_path
        self._avatar_fallback_text = "Baldi\nis\nwatching!"
        self._title_text_ready = "Baldi is ready to help!\nAsk anything, but write neatly!"
        self._title_text_thinking = "Baldi is thinking...\nGive him a moment to respond!"
        self._title_label: Optional[ttk.Label] = None

        self._conversation: ScrolledText
        self._input_box: tk.Text
        self._send_button: ttk.Button
        self._avatar_label: ttk.Label
        self._avatar_image_default: Optional[ImageTk.PhotoImage] = None
        self._avatar_image_thinking: Optional[ImageTk.PhotoImage] = None
        self._background_label: tk.Label
        self._background_photo: Optional[ImageTk.PhotoImage] = None
        self._last_bg_size: tuple[int, int] = (0, 0)
        self._bookshelf_files: list[Path] = []
        self._bookshelf_listbox: Optional[tk.Listbox] = None
        self._on_bookshelf_change: Optional[Callable[[tuple[Path, ...]], None]] = None

        self._build_ui()
        self._root.protocol("WM_DELETE_WINDOW", self._handle_close_event)

    # Public API -----------------------------------------------------------------
    def set_on_send(self, callback: Callable[[str], bool]) -> None:
        self._on_send = callback

    def set_on_close(self, callback: Callable[[], bool | None]) -> None:
        self._on_close = callback

    def set_on_character_select(self, callback: Callable[[], None]) -> None:
        self._on_character_select = callback

    def set_on_bookshelf_change(
        self, callback: Callable[[tuple[Path, ...]], None]
    ) -> None:
        self._on_bookshelf_change = callback

    def get_bookshelf_files(self) -> tuple[Path, ...]:
        return tuple(self._bookshelf_files)

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

    def update_character(self, character_name: str, avatar_path: Path, thinking_path: Optional[Path]) -> None:
        """Update the character avatar and name."""
        self._avatar_path = avatar_path
        self._thinking_path = thinking_path

        # Reload avatar images
        self._avatar_image_default = self._create_photo_image(self._avatar_path)
        if self._thinking_path is not None:
            self._avatar_image_thinking = self._create_photo_image(self._thinking_path)
        else:
            self._avatar_image_thinking = None

        # Update the displayed avatar
        self._update_avatar_state()

        # Update window title
        self._root.title(f"{character_name}'s Notebook of Knowledge")

        # Update title text
        self._title_text_ready = f"{character_name} is ready to help!\nAsk anything, but write neatly!"
        self._title_text_thinking = f"{character_name} is thinking...\nGive them a moment to respond!"
        if self._title_label:
            self._title_label.configure(text=self._title_text_ready if not self._is_pending else self._title_text_thinking)

    # Internal helpers -----------------------------------------------------------
    def _build_ui(self) -> None:
        self._background_label = tk.Label(self._root, bd=0)
        self._background_label.place(x=0, y=0, relwidth=1, relheight=1)
        self._background_label.lower()

        main_pane = ttk.Frame(self._root, style="GlassMain.TFrame", padding=12)
        main_pane.pack(fill="both", expand=True, padx=16, pady=16)
        main_pane.columnconfigure(0, weight=3)
        main_pane.columnconfigure(1, weight=1)
        main_pane.rowconfigure(1, weight=1)

        header = ttk.Frame(main_pane, style="GlassMain.TFrame")
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.columnconfigure(0, weight=1)

        info_header = ttk.Frame(header, style="GlassMain.TFrame")
        info_header.grid(row=0, column=0, sticky="w")

        avatar_frame = ttk.Frame(info_header, style="GlassMain.TFrame")
        avatar_frame.pack(side="left", anchor="n", padx=(0, 24))
        self._load_avatar(avatar_frame)

        title_label = ttk.Label(
            info_header,
            text=self._title_text_ready,
            style="Heading.TLabel",
            justify="left",
        )
        title_label.pack(side="left", anchor="n")
        self._title_label = title_label

        add_books_button = ttk.Button(
            header,
            text="Add to Bookshelf",
            style="GlassAccent.TButton",
            command=self._handle_add_bookshelf_files,
        )
        add_books_button.grid(row=0, column=1, sticky="ne")

        # Main conversation area
        conversation_frame = ttk.Frame(
            main_pane,
            style="GlassPanel.TFrame",
            padding=8,
        )
        conversation_frame.configure(borderwidth=1, relief="solid")
        conversation_frame.grid(row=1, column=0, sticky="nsew", pady=(12, 8), padx=(0, 12))

        self._conversation = ScrolledText(
            conversation_frame,
            wrap="word",
            state="disabled",
            height=20,
            padx=8,
            pady=8,
        )
        self._conversation.pack(fill="both", expand=True)
        self._theme.configure_text_widget(self._conversation)

        # Bookshelf panel
        bookshelf_frame = ttk.Frame(
            main_pane,
            style="GlassPanel.TFrame",
            padding=8,
        )
        bookshelf_frame.configure(borderwidth=1, relief="solid")
        bookshelf_frame.grid(row=1, column=1, sticky="ns", pady=(12, 8))
        bookshelf_frame.columnconfigure(0, weight=1)
        bookshelf_frame.rowconfigure(1, weight=1)

        bookshelf_label = ttk.Label(
            bookshelf_frame,
            text="Bookshelf",
            style="Heading.TLabel",
            anchor="center",
            justify="center",
        )
        bookshelf_label.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        list_container = ttk.Frame(bookshelf_frame, style="GlassMain.TFrame")
        list_container.grid(row=1, column=0, sticky="nsew")
        list_container.columnconfigure(0, weight=1)
        list_container.rowconfigure(0, weight=1)

        self._bookshelf_listbox = tk.Listbox(
            list_container,
            height=12,
            selectmode="extended",
            activestyle="dotbox",
            borderwidth=0,
            highlightthickness=0,
            font=("Segoe UI", 10),
        )
        self._bookshelf_listbox.grid(row=0, column=0, sticky="nsew")
        self._bookshelf_listbox.configure(
            bg="#ffffff",
            fg="#1e293b",
            selectbackground="#bae6fd",
            selectforeground="#0f172a",
            highlightbackground="#e2e8f0",
        )
        self._bookshelf_listbox.bind("<Delete>", self._on_bookshelf_delete_key)

        list_scroll = ttk.Scrollbar(
            list_container, orient="vertical", command=self._bookshelf_listbox.yview
        )
        list_scroll.grid(row=0, column=1, sticky="ns")
        self._bookshelf_listbox.configure(yscrollcommand=list_scroll.set)

        bookshelf_controls = ttk.Frame(bookshelf_frame, style="GlassMain.TFrame")
        bookshelf_controls.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        bookshelf_controls.columnconfigure(0, weight=1)
        bookshelf_controls.columnconfigure(1, weight=1)

        remove_button = ttk.Button(
            bookshelf_controls,
            text="Remove Selected",
            command=self._remove_selected_bookshelf_files,
        )
        remove_button.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        clear_button = ttk.Button(
            bookshelf_controls,
            text="Clear All",
            command=self._clear_bookshelf_files,
        )
        clear_button.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        self._refresh_bookshelf_list()

        # Bottom section for input and controls
        bottom_frame = ttk.Frame(main_pane, style="GlassMain.TFrame")
        bottom_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        bottom_frame.columnconfigure(0, weight=1)

        input_box_container = ttk.Frame(
            bottom_frame,
            style="GlassPanel.TFrame",
            padding=4,
        )
        input_box_container.configure(borderwidth=1, relief="solid")
        input_box_container.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        # Create the input box with clear styling
        self._input_box = tk.Text(
            input_box_container,
            height=3,
            wrap="word",
            font=("Segoe UI", 11),
            bd=0,
            highlightthickness=1,
            highlightbackground="#e2e8f0",
            highlightcolor="#38bdf8",
        )
        self._input_box.pack(fill="both", expand=True, padx=2, pady=2)
        
        # Configure input box colors and appearance
        self._input_box.configure(
            bg="#ffffff",  # Pure white background
            fg="#1e293b",  # Dark text color
            insertbackground="#38bdf8",  # Cursor color
            insertwidth=2,  # Make cursor more visible
            relief="flat",
            padx=12,
            pady=8,
        )
        
        # Add placeholder text with gray color
        self._input_box.insert("1.0", "Type your message here...")
        self._input_box.configure(foreground="#94a3b8")

        def on_focus_in(event):
            if self._input_box.get("1.0", "end-1c").strip() == "Type your message here...":
                self._input_box.delete("1.0", "end")
                self._input_box.configure(foreground="#1e293b")

        def on_focus_out(event):
            if not self._input_box.get("1.0", "end-1c").strip():
                self._input_box.delete("1.0", "end")
                self._input_box.insert("1.0", "Type your message here...")
                self._input_box.configure(foreground="#94a3b8")

        self._input_box.bind("<FocusIn>", on_focus_in)
        self._input_box.bind("<FocusOut>", on_focus_out)
        self._input_box.bind("<Return>", self._on_return_pressed)
        self._input_box.bind("<Shift-Return>", self._on_shift_return_pressed)

        self._send_button = ttk.Button(
            bottom_frame,
            text="Send",
            command=self._handle_send_event,
            style="GlassAccent.TButton",
        )
        self._send_button.grid(row=0, column=1, sticky="e")

        status_bar = ttk.Label(
            main_pane,
            textvariable=self._status_var,
            style="Status.TLabel",
            anchor="w",
        )
        status_bar.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(12, 0))

        self._root.bind("<Configure>", self._handle_window_resize)
        self._root.update_idletasks()
        self._update_background_image(self._root.winfo_width(), self._root.winfo_height())

        self._input_box.focus_set()

    def _handle_add_bookshelf_files(self) -> None:
        if self._bookshelf_listbox is None:
            return

        filenames = filedialog.askopenfilenames(
            parent=self._root,
            title="Select documents for the bookshelf",
            filetypes=[
                ("Supported documents", "*.pdf *.txt"),
                ("PDF files", "*.pdf"),
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ],
        )
        if not filenames:
            return

        unsupported: list[str] = []
        added = False
        for raw_name in filenames:
            path = Path(raw_name).expanduser()
            try:
                resolved = path.resolve(strict=True)
            except FileNotFoundError:
                unsupported.append(f"{path} (not found)")
                continue
            suffix = resolved.suffix.lower()
            if suffix not in {".pdf", ".txt"}:
                unsupported.append(f"{resolved.name} (unsupported type)")
                continue
            if resolved in self._bookshelf_files:
                continue
            self._bookshelf_files.append(resolved)
            added = True

        if added:
            self._refresh_bookshelf_list()
            self._notify_bookshelf_change()

        if unsupported:
            messagebox.showwarning(
                "Some files were skipped",
                "The following files could not be added:\n"
                + "\n".join(f"- {item}" for item in unsupported),
                parent=self._root,
            )

    def _remove_selected_bookshelf_files(self) -> None:
        if self._bookshelf_listbox is None:
            return
        selection = list(self._bookshelf_listbox.curselection())
        if not selection:
            return
        for index in sorted(selection, reverse=True):
            if 0 <= index < len(self._bookshelf_files):
                del self._bookshelf_files[index]
        self._refresh_bookshelf_list()
        self._notify_bookshelf_change()

    def _clear_bookshelf_files(self) -> None:
        if not self._bookshelf_files:
            return
        self._bookshelf_files.clear()
        self._refresh_bookshelf_list()
        self._notify_bookshelf_change()

    def _refresh_bookshelf_list(self) -> None:
        if self._bookshelf_listbox is None:
            return
        self._bookshelf_listbox.delete(0, "end")
        for path in self._bookshelf_files:
            self._bookshelf_listbox.insert("end", self._format_bookshelf_display(path))

    def _notify_bookshelf_change(self) -> None:
        if self._on_bookshelf_change is None:
            return
        self._on_booksfhelf_change(tuple(self._bookshelf_files))

    def _format_bookshelf_display(self, path: Path) -> str:
        try:
            display_path = path.resolve()
        except OSError:
            display_path = path
        return f"{display_path.name} ({display_path.parent})"

    def _on_bookshelf_delete_key(self, event: tk.Event) -> str:
        self._remove_selected_bookshelf_files()
        return "break"

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
        self._avatar_label = ttk.Label(
            container,
            anchor="center",
            justify="center",
            style="GlassAvatar.TLabel",
            cursor="hand2",
        )
        self._avatar_label.pack()
        self._avatar_label.bind("<Button-1>", self._handle_avatar_click)

        self._avatar_image_default = self._create_photo_image(self._avatar_path)
        if self._thinking_path is not None:
            self._avatar_image_thinking = self._create_photo_image(self._thinking_path)
        self._update_avatar_state()

    def _handle_avatar_click(self, event=None) -> None:
        """Handle avatar click to open character selector."""
        if self._on_character_select:
            self._on_character_select()

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
                # We pass the raw text, *without* the $$ delimiters
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
                # We pass the raw math segment (e.g., "x^2 + \frac{a}{b}")
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
                    # We store the content *without* the $$
                    segments.append((True, text[i + 2 : end]))
                    i = end + 2
                    continue
            if text[i] == "$":
                end = text.find("$", i + 1)
                if end != -1:
                    if buffer:
                        segments.append((False, "".join(buffer)))
                        buffer.clear()
                    # We store the content *without* the $
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

    # --- MODIFIED ---
    # This function is now greatly simplified.
    # It no longer tries to parse or sanitize the math.
    # It just inserts the raw text with the 'math' tag.
    def _insert_math_inline(
        self,
        text: str,
        base_tag: str,
        extra_tags: tuple[str, ...],
    ) -> None:
        """
        Inserts the raw, unmodified LaTeX string with the math style.
        This will not render the math, but will display the LaTeX code
        in the styled (italic, blue) font without destroying it.
        """
        if text:
            # We add the '$' back for display, since _split_math_segments
            # removed them. This makes it clear it's a math segment.
            # We don't add $$ for block, as the block tag handles centering.
            
            # is_block = "math_block" in extra_tags # No longer needed
            # display_text = text if is_block else f"${text}$" # This was the incorrect part

            self._conversation.insert(
                "end",
                text, # Just insert the raw text (e.g., "e" or "x^2")
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
        
        # We now pass the raw text to _insert_math_inline
        # which will apply the 'math_block' tag.
        self._insert_math_inline(text, base_tag, ("math_block",))

    # --- REMOVED ---
    # This function was the source of the problem. It was destroying
    # the LaTeX. It is no longer needed.
    #
    # def _sanitize_math_text(self, text: str) -> str:
    #     cleaned = text.replace(r"\,", " ")
    #     ...
    #     return cleaned

    def _handle_window_resize(self, event: tk.Event) -> None:
        if event.widget is self._root:
            self._update_background_image(event.width, event.height)

    def _update_background_image(self, width: int, height: int) -> None:
        if width <= 0 or height <= 0:
            return
        size = (width, height)
        if size == self._last_bg_size:
            return
        self._last_bg_size = size
        image = self._create_glass_background(width, height)
        self._background_photo = ImageTk.PhotoImage(image)
        self._background_label.configure(image=self._background_photo)

    def _create_glass_background(self, width: int, height: int) -> Image.Image:
        height = max(height, 1)
        gradient = Image.new("RGB", (1, height))
        draw = ImageDraw.Draw(gradient)
        top_color = (15, 23, 42)
        bottom_color = (30, 64, 175)
        for y in range(height):
            factor = y / max(height - 1, 1)
            color = tuple(
                int(top + (bottom - top) * factor)
                for top, bottom in zip(top_color, bottom_color)
            )
            draw.point((0, y), fill=color)
        gradient = gradient.resize((width, height), Image.BILINEAR)
        gradient = gradient.convert("RGBA")

        overlay = Image.new("RGBA", (width, height), (255, 255, 255, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.ellipse(
            (
                -int(width * 0.25),
                -int(height * 0.35),
                int(width * 0.75),
                int(height * 0.45),
            ),
            fill=(255, 255, 255, 70),
        )
        overlay_draw.rectangle(
            (
                int(width * 0.55),
                int(height * 0.1),
                int(width * 1.05),
                int(height * 0.7),
            ),
            fill=(93, 232, 249, 55),
        )
        overlay_draw.ellipse(
            (
                int(width * 0.35),
                int(height * 0.55),
                int(width * 1.15),
                int(height * 1.35),
            ),
            fill=(110, 231, 183, 55),
        )

        combined = Image.alpha_composite(gradient, overlay)
        return combined.filter(ImageFilter.GaussianBlur(radius=18))

    def _update_avatar_state(self) -> None:
        thinking_active = self._is_pending and self._avatar_image_thinking is not None
        if thinking_active:
            self._avatar_label.configure(
                image=self._avatar_image_thinking,
                text="",
                style="GlassAvatar.TLabel",
                padding=0,
            )
        elif self._avatar_image_default is not None:
            self._avatar_label.configure(
                image=self._avatar_image_default,
                text="",
                style="GlassAvatar.TLabel",
                padding=0,
            )
        elif self._avatar_image_thinking is not None:
            self._avatar_label.configure(
                image=self._avatar_image_thinking,
                text="",
                style="GlassAvatar.TLabel",
                padding=0,
            )
        else:
            self._avatar_label.configure(
                image="",
                text=self._avatar_fallback_text,
                style="GlassAvatar.TLabel",
                padding=12,
            )
        if self._title_label is not None:
            if thinking_active:
                self._title_label.configure(text=self._title_text_thinking)
            else:
                self._title_label.configure(text=self._title_text_ready)

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