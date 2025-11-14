"""Character selection dialog UI."""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional
from pathlib import Path
from PIL import Image, ImageTk

from .characters import CHARACTERS, CharacterConfig


class CharacterSelectorDialog:
    """Modal dialog for selecting a character persona."""

    def __init__(
        self,
        parent: tk.Tk,
        on_select: Callable[[CharacterConfig], None],
        current_character_id: str = "baldi",
    ) -> None:
        self.parent = parent
        self.on_select = on_select
        self.current_character_id = current_character_id
        self.selected_character: Optional[CharacterConfig] = None
        self.image_refs = []  # Keep references to prevent garbage collection

        # Create toplevel dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Select Your Teacher")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Set dialog size and position
        dialog_width = 800
        dialog_height = 600
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        x = (screen_width - dialog_width) // 2
        y = (screen_height - dialog_height) // 2
        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")

        # Configure dark background
        bg_color = "#1e293b"
        self.dialog.configure(bg=bg_color)
        self.dialog.resizable(False, False)

        # Create UI
        self._create_ui()

    def _create_ui(self) -> None:
        """Create the character selection UI."""
        # Title
        title_frame = tk.Frame(self.dialog, bg="#1e293b", pady=20)
        title_frame.pack(fill=tk.X)

        title_label = tk.Label(
            title_frame,
            text="Choose Your Teacher",
            font=("Segoe UI", 24, "bold"),
            fg="#f8fafc",
            bg="#1e293b",
        )
        title_label.pack()

        subtitle_label = tk.Label(
            title_frame,
            text="Select a character to begin your learning adventure",
            font=("Segoe UI", 12),
            fg="#94a3b8",
            bg="#1e293b",
        )
        subtitle_label.pack(pady=(5, 0))

        # Character grid container
        grid_container = tk.Frame(self.dialog, bg="#1e293b")
        grid_container.pack(expand=True, fill=tk.BOTH, padx=40, pady=20)

        # Configure grid weights for 2x2 layout
        for i in range(2):
            grid_container.grid_rowconfigure(i, weight=1)
            grid_container.grid_columnconfigure(i, weight=1)

        # Create character cards
        character_list = list(CHARACTERS.values())
        for idx, character in enumerate(character_list):
            row = idx // 2
            col = idx % 2
            card = self._create_character_card(grid_container, character)
            card.grid(row=row, column=col, padx=15, pady=15, sticky="nsew")

    def _load_character_image(
        self, parent: tk.Frame, character: CharacterConfig, card_bg: str
    ) -> tk.Label:
        """Load and display the character's thinking image."""
        # Get the path to the thinking image, try both .png and .webp
        assets_dir = Path(__file__).parent.parent.parent / "assets"
        base_path = assets_dir / character.thinking_path

        # Try to find the image with either .png or .webp extension
        image_path = None
        base_path_str = str(base_path)

        # Remove extension if present
        if base_path_str.endswith('.png') or base_path_str.endswith('.webp'):
            base_path_no_ext = Path(base_path_str.rsplit('.', 1)[0])
        else:
            base_path_no_ext = base_path

        # Try both extensions
        for ext in ['.png', '.webp']:
            candidate = Path(str(base_path_no_ext) + ext)
            if candidate.exists():
                image_path = candidate
                break

        if not image_path:
            # If neither exists, use the original path for error message
            image_path = base_path

        try:
            # Load and resize the image
            pil_image = Image.open(image_path)
            pil_image = pil_image.resize((120, 120), Image.Resampling.LANCZOS)

            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(pil_image)
            self.image_refs.append(photo)  # Keep reference

            # Create label with image
            icon_label = tk.Label(
                parent,
                image=photo,
                bg="#475569",
            )
            icon_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

            return icon_label
        except Exception as e:
            # Fallback to text initial if image loading fails
            print(f"Warning: Could not load image for {character.name}: {e}")
            icon_label = tk.Label(
                parent,
                text=character.name[0],
                font=("Segoe UI", 48, "bold"),
                fg="#38bdf8",
                bg="#475569",
            )
            icon_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
            return icon_label

    def _create_character_card(
        self, parent: tk.Frame, character: CharacterConfig
    ) -> tk.Frame:
        """Create a single character selection card."""
        # Card frame with dark background
        card_bg = "#334155"
        card_hover_bg = "#475569"

        card = tk.Frame(
            parent,
            bg=card_bg,
            relief=tk.FLAT,
            borderwidth=0,
            cursor="hand2",
        )

        # Add rounded corners effect with padding
        inner_frame = tk.Frame(card, bg=card_bg, padx=20, pady=20)
        inner_frame.pack(expand=True, fill=tk.BOTH)

        # Character image placeholder (large circle or square)
        image_container = tk.Frame(
            inner_frame,
            bg="#475569",
            width=120,
            height=120,
        )
        image_container.pack(pady=(10, 20))
        image_container.pack_propagate(False)

        # Load and display character thinking image
        icon_label = self._load_character_image(
            image_container, character, card_bg
        )

        # Character name
        name_label = tk.Label(
            inner_frame,
            text=character.name,
            font=("Segoe UI", 18, "bold"),
            fg="#f8fafc",
            bg=card_bg,
        )
        name_label.pack(pady=(0, 10))

        # Character description
        desc_label = tk.Label(
            inner_frame,
            text=character.description,
            font=("Segoe UI", 11),
            fg="#cbd5e1",
            bg=card_bg,
            wraplength=250,
            justify=tk.CENTER,
        )
        desc_label.pack()

        # Current selection indicator
        if character.id == self.current_character_id:
            indicator = tk.Label(
                inner_frame,
                text="✓ Current",
                font=("Segoe UI", 10, "bold"),
                fg="#22c55e",
                bg=card_bg,
            )
            indicator.pack(pady=(15, 0))

        # Bind click events to all widgets in the card
        def on_card_click(event=None):
            self._select_character(character)

        def on_enter(event):
            card.configure(bg=card_hover_bg)
            inner_frame.configure(bg=card_hover_bg)
            name_label.configure(bg=card_hover_bg)
            desc_label.configure(bg=card_hover_bg)

        def on_leave(event):
            card.configure(bg=card_bg)
            inner_frame.configure(bg=card_bg)
            name_label.configure(bg=card_bg)
            desc_label.configure(bg=card_bg)

        # Bind events to all elements for better UX
        for widget in [card, inner_frame, image_container, icon_label, name_label, desc_label]:
            widget.bind("<Button-1>", on_card_click)
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

        return card

    def _select_character(self, character: CharacterConfig) -> None:
        """Handle character selection."""
        self.selected_character = character
        self.dialog.destroy()
        self.on_select(character)

    def show(self) -> None:
        """Show the dialog and wait for user interaction."""
        self.dialog.wait_window()


def show_character_selector(
    parent: tk.Tk,
    on_select: Callable[[CharacterConfig], None],
    current_character_id: str = "baldi",
) -> None:
    """Show the character selection dialog.

    Args:
        parent: Parent window
        on_select: Callback function called when a character is selected
        current_character_id: ID of the currently selected character
    """
    dialog = CharacterSelectorDialog(parent, on_select, current_character_id)
    dialog.show()


__all__ = ["CharacterSelectorDialog", "show_character_selector"]
