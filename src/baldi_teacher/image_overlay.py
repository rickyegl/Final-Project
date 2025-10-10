from __future__ import annotations

import threading
import sys
from pathlib import Path
from typing import Optional

try:
    import tkinter as tk
except ImportError:  # pragma: no cover - tkinter missing on some installs
    tk = None  # type: ignore[misc]

try:
    from PIL import Image, ImageTk, ImageColor
except ImportError:  # pragma: no cover
    Image = None  # type: ignore[assignment]
    ImageTk = None  # type: ignore[assignment]
    ImageColor = None  # type: ignore[assignment]


class ImageOverlay:
    """Displays an image in a frameless window anchored to the screen corner."""

    def __init__(
        self,
        image_path: Path,
        *,
        anchor: str = "sw",
        padding: int = 24,
        topmost: bool = True,
        max_width: Optional[int] = 320,
        max_height: Optional[int] = 320,
        transparent: Optional[bool] = None,
    ) -> None:
        self._image_path = Path(image_path)
        self._anchor = anchor.lower()
        self._padding = padding
        self._topmost = topmost
        self._max_width = max_width
        self._max_height = max_height
        self._transparent = (
            transparent
            if transparent is not None
            else sys.platform.startswith("win")
        )
        self._bg_color = "#00FF00" if self._transparent else "#FFFFFF"
        if tk is None:
            raise RuntimeError("tkinter is required for the Baldi overlay window.")
        if Image is None or ImageTk is None:
            raise RuntimeError(
                "Pillow is required for the Baldi overlay. Install with 'pip install Pillow'."
            )
        if ImageColor is None:
            raise RuntimeError(
                "Pillow ImageColor module missing. Ensure Pillow is correctly installed."
            )

        self._stop_event = threading.Event()
        self._ready_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._root: Optional[tk.Tk] = None
        self._photo = None  # keep ref to avoid GC

    def start(self, timeout: float = 5.0) -> None:
        if self._thread is not None:
            return
        if not self._image_path.exists():
            raise FileNotFoundError(f"Overlay image not found: {self._image_path}")

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._ready_event.wait(timeout=timeout)

    def stop(self) -> None:
        self._stop_event.set()
        if self._root is not None:
            try:
                self._root.after(0, self._root.destroy)
            except tk.TclError:
                pass
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._thread = None
        self._root = None
        self._photo = None
        self._stop_event.clear()
        self._ready_event.clear()

    def _run(self) -> None:
        assert Image is not None  # for mypy
        assert tk is not None
        assert ImageTk is not None

        try:
            image = Image.open(self._image_path)
        except Exception as exc:  # pragma: no cover - runtime problem
            self._ready_event.set()
            raise RuntimeError(f"Failed to load overlay image: {exc}") from exc

        image = _resize_if_needed(
            image,
            max_width=self._max_width,
            max_height=self._max_height,
        )

        root = tk.Tk()
        root.overrideredirect(True)
        root.configure(background=self._bg_color)
        if self._topmost:
            root.attributes("-topmost", True)
        if self._transparent:
            try:
                root.wm_attributes("-transparentcolor", self._bg_color)
            except tk.TclError:
                # Some Tk builds may not support transparentcolor; fall back to opaque.
                self._transparent = False
                self._bg_color = "#FFFFFF"
                root.configure(background=self._bg_color)
        root.resizable(False, False)

        image = _prepare_image(
            image,
            transparent=self._transparent,
            chroma_color=self._bg_color,
        )

        # Convert to Tk image and keep reference.
        self._photo = ImageTk.PhotoImage(image)
        label = tk.Label(
            root,
            image=self._photo,
            borderwidth=0,
            highlightthickness=0,
            background=root["background"],
        )
        label.pack()

        width, height = image.size
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x, y = _calculate_position(self._anchor, screen_width, screen_height, width, height, self._padding)
        root.geometry(f"{width}x{height}+{x}+{y}")

        self._root = root
        self._ready_event.set()

        def poll_stop() -> None:
            if self._stop_event.is_set():
                try:
                    root.destroy()
                except tk.TclError:
                    pass
            else:
                root.after(200, poll_stop)

        root.after(200, poll_stop)

        try:
            root.mainloop()
        finally:
            self._root = None
            self._thread = None
            self._photo = None


def _calculate_position(
    anchor: str,
    screen_width: int,
    screen_height: int,
    width: int,
    height: int,
    padding: int,
) -> tuple[int, int]:
    anchor = anchor.lower()
    if "w" in anchor:
        x = padding
    elif "e" in anchor:
        x = max(padding, screen_width - width - padding)
    else:
        x = (screen_width - width) // 2

    if "n" in anchor:
        y = padding
    elif "s" in anchor:
        y = max(padding, screen_height - height - padding)
    else:
        y = (screen_height - height) // 2

    return x, y


def _resize_if_needed(
    image: "Image.Image",
    *,
    max_width: Optional[int],
    max_height: Optional[int],
) -> "Image.Image":
    width, height = image.size
    scale = 1.0

    if max_width is not None and width > max_width:
        scale = min(scale, max_width / width) if scale != 1.0 else max_width / width
    if max_height is not None and height > max_height:
        scale = min(scale, max_height / height) if scale != 1.0 else max_height / height

    if scale >= 1.0:
        return image

    new_width = max(1, int(width * scale))
    new_height = max(1, int(height * scale))
    return image.resize((new_width, new_height), Image.LANCZOS)


def _prepare_image(
    image: "Image.Image",
    *,
    transparent: bool,
    chroma_color: str,
) -> "Image.Image":
    if not transparent:
        return image.convert("RGBA")

    image = image.convert("RGBA")
    chroma = ImageColor.getrgb(chroma_color)
    bg = Image.new("RGBA", image.size, chroma)
    bg.paste(image, mask=image.split()[-1])  # use alpha channel as mask
    return bg.convert("RGB")
