from __future__ import annotations

import re
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, font as tkfont, messagebox
from tkinter import ttk
from typing import Callable, Optional
import html as html_module

from PIL import Image, ImageDraw, ImageFilter, ImageTk
from tkinterweb import HtmlFrame


BOLD_PATTERN = re.compile(r"\*(.+?)\*")


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

    def get_css(self) -> str:
        """Generate CSS for the HTML view."""
        return """
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                font-size: 12pt;
                background-color: #f9faff;
                color: #0f172a;
                margin: 8px;
                padding: 8px;
            }
            .message {
                margin-bottom: 16px;
            }
            .label-user {
                color: #0ea5e9;
                font-weight: bold;
            }
            .label-baldi {
                color: #a855f7;
                font-weight: bold;
            }
            .label-system {
                color: #ec4899;
                font-weight: bold;
            }
            .text-user {
                color: #0f172a;
            }
            .text-baldi {
                color: #1e293b;
            }
            .text-system {
                color: #be123c;
            }
            strong, b {
                font-weight: bold;
            }
            em, i {
                font-style: italic;
            }
            h1 {
                font-size: 15pt;
                font-weight: bold;
                margin-top: 6px;
                margin-bottom: 6px;
            }
            h2 {
                font-size: 13pt;
                font-weight: bold;
                margin-top: 6px;
                margin-bottom: 6px;
            }
            h3 {
                font-size: 12pt;
                font-weight: bold;
                margin-top: 4px;
                margin-bottom: 4px;
            }
            ul {
                margin-left: 24px;
                margin-top: 2px;
                margin-bottom: 2px;
            }
            li {
                margin-top: 2px;
                margin-bottom: 2px;
            }
            .separator {
                color: #cbd5f5;
                margin-top: 6px;
                margin-bottom: 6px;
            }
            .math-inline {
                color: #0284c7;
            }
            .math-block {
                color: #0284c7;
                text-align: center;
                margin-top: 8px;
                margin-bottom: 8px;
                display: block;
            }
        </style>
        """

    def get_mathjax_config(self) -> str:
        """Get MathJax configuration script."""
        return """
        <script>
            MathJax = {
                tex: {
                    // --- THIS IS THE FIX ---
                    // Added ['\\(', '\\)'] to the inlineMath array.
                    inlineMath: [['$', '$'], ['\\(', '\\)']],
                    // --- END OF FIX ---
                    displayMath: [['$$', '$$']],
                    processEscapes: true,
                    processEnvironments: true
                },
                options: {
                    skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre']
                },
                startup: {
                    pageReady: () => {
                        return MathJax.startup.defaultPageReady().then(() => {
                            console.log('MathJax loaded');
                        });
                    }
                }
            };
        </script>
        <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js" id="MathJax-script" async></script>
        """


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
        self._root.minsize(640, 480)
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

        self._conversation: HtmlFrame
        self._conversation_html: list[str] = []
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
        self._append_message("You", text, "user")

    def show_baldi_message(self, text: str) -> None:
        self._append_message("Baldi", text, "baldi")

    def show_system_message(self, text: str) -> None:
        self._append_message("System", text, "system")

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

        # Main conversation area with HtmlFrame
        conversation_frame = ttk.Frame(
            main_pane,
            style="GlassPanel.TFrame",
            padding=8,
        )
        conversation_frame.configure(borderwidth=1, relief="solid")
        conversation_frame.grid(row=1, column=0, sticky="nsew", pady=(12, 8), padx=(0, 12))

        self._conversation = HtmlFrame(conversation_frame, messages_enabled=False)
        self._conversation.pack(fill="both", expand=True)

        # Initialize with base HTML structure
        self._init_conversation_html()

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
            bg="#ffffff",
            fg="#1e293b",
            insertbackground="#38bdf8",
            insertwidth=2,
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

    def _init_conversation_html(self) -> None:
        """Initialize the conversation with base HTML structure including MathJax."""
        base_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            {self._theme.get_mathjax_config()}
            {self._theme.get_css()}
        </head>
        <body>
            <div id="messages">
            </div>
        </body>
        </html>
        """
        self._conversation.load_html(base_html)
        self._conversation_html = []

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
            if resolved in self._booksFhelf_files:
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
        self._on_bookshelf_change(tuple(self._bookshelf_files))

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

    def _append_message(self, speaker: str, text: str, message_type: str) -> None:
        """Append a message to the conversation as HTML."""
        html_content = self._format_message_html(speaker, text, message_type)
        self._conversation_html.append(html_content)
        self._update_conversation_display()

    def _format_message_html(self, speaker: str, text: str, message_type: str) -> str:
        """Format a message as HTML with MathJax support."""
        escaped_speaker = html_module.escape(speaker)
        formatted_text = self._text_to_html(text, message_type)

        return f"""
        <div class="message">
            <span class="label-{message_type}">{escaped_speaker}&gt;</span>
            <span class="text-{message_type}">{formatted_text}</span>
        </div>
        """

    def _text_to_html(self, text: str, message_type: str) -> str:
        """Convert markdown-like text to HTML with LaTeX support."""
        lines = text.splitlines()
        if not lines:
            return ""

        html_parts = []
        for line in lines:
            stripped = line.strip()

            if stripped == "":
                html_parts.append("<br>")
                continue

            if stripped == "***":
                html_parts.append('<div class="separator">------------------------------------------------</div>')
                continue

            # Block math $$...$$
            if stripped.startswith("$$") and stripped.endswith("$$") and len(stripped) > 4:
                math_content = stripped[2:-2].strip()
                html_parts.append(f'<div class="math-block">$$\\displaystyle {math_content}$$</div>')
                continue

            # Headings
            if stripped.startswith("### "):
                content = stripped[4:].strip()
                content_html = self._process_inline_formatting(content)
                html_parts.append(f"<h3>{content_html}</h3>")
                continue
            elif stripped.startswith("## "):
                content = stripped[3:].strip()
                content_html = self._process_inline_formatting(content)
                html_parts.append(f"<h2>{content_html}</h2>")
                continue
            elif stripped.startswith("# "):
                content = stripped[2:].strip()
                content_html = self._process_inline_formatting(content)
                html_parts.append(f"<h1>{content_html}</h1>")
                continue

            # Bullet points
            if stripped.startswith(("- ", "* ")):
                content = stripped[2:].strip()
                content_html = self._process_inline_formatting(content)
                html_parts.append(f"<ul><li>{content_html}</li></ul>")
                continue

            # Regular paragraph
            content_html = self._process_inline_formatting(line)
            html_parts.append(f"<p>{content_html}</p>")

        return "\n".join(html_parts)

    def _process_inline_formatting(self, text: str) -> str:
        """Process inline formatting including bold and inline math."""
        result_parts = []

        # Split by math segments first
        segments = self._split_math_segments(text)

        for is_math, segment in segments:
            if not segment:
                continue

            if is_math:
                # Inline math - wrap with MathJax delimiters
                result_parts.append(f'<span class="math-inline">\\({segment}\\)</span>')
            else:
                # Process bold formatting in non-math segments
                cursor = 0
                for match in BOLD_PATTERN.finditer(segment):
                    # Add text before the match
                    if cursor < match.start():
                        result_parts.append(html_module.escape(segment[cursor:match.start()]))
                    # Add bold text
                    bold_text = html_module.escape(match.group(1))
                    result_parts.append(f"<strong>{bold_text}</strong>")
                    cursor = match.end()
                # Add remaining text
                if cursor < len(segment):
                    result_parts.append(html_module.escape(segment[cursor:]))

        return "".join(result_parts)

    def _split_math_segments(self, text: str) -> list[tuple[bool, str]]:
        """Split text into math and non-math segments."""
        segments: list[tuple[bool, str]] = []
        buffer: list[str] = []
        i = 0
        length = len(text)

        while i < length:
            # Check for $$...$$
            if text.startswith("$$", i):
                end = text.find("$$", i + 2)
                if end != -1:
                    if buffer:
                        segments.append((False, "".join(buffer)))
                        buffer.clear()
                    segments.append((True, text[i + 2:end]))
                    i = end + 2
                    continue

            # --- THIS IS THE FIX ---
            # Added check for \( ... \) delimiters
            # Check for \(...\)
            if text.startswith("\\(", i):
                end = text.find("\\)", i + 2)
                if end != -1:
                    if buffer:
                        segments.append((False, "".join(buffer)))
                        buffer.clear()
                    segments.append((True, text[i + 2:end]))
                    i = end + 2
                    continue
            # --- END OF FIX ---
            
            # Check for $...$
            if text[i] == "$":
                end = text.find("$", i + 1)
                if end != -1:
                    if buffer:
                        segments.append((False, "".join(buffer)))
                        buffer.clear()
                    segments.append((True, text[i + 1:end]))
                    i = end + 1
                    continue

            buffer.append(text[i])
            i += 1

        if buffer:
            segments.append((False, "".join(buffer)))

        return segments

    def _update_conversation_display(self) -> None:
        """Update the HTML display with all messages and trigger MathJax rendering."""
        messages_html = "\n".join(self._conversation_html)

        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            {self._theme.get_mathjax_config()}
            {self._theme.get_css()}
        </head>
        <body>
            <div id="messages">
                {messages_html}
            </div>
            <script>
                // Scroll to bottom after rendering
                window.onload = function() {{
                    window.scrollTo(0, document.body.scrollHeight);

                    // Re-render MathJax if available
                    if (typeof MathJax !== 'undefined' && MathJax.typesetPromise) {{
                        MathJax.typesetPromise();
                    }}
                }};
            </script>
        </body>
        </html>
        """

        self._conversation.load_html(full_html)

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