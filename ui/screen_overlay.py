"""
KiroNav Screen Overlay — Floating popup hints at screen positions

Shows styled popup tooltips at x,y screen coordinates.
Each popup is a small frameless always-on-top window.
"""

import sys
import threading
from typing import Optional

if sys.platform != "win32":
    raise ImportError("screen_overlay is Windows-only")

import tkinter as tk

# Visual config
POPUP_BG = "#1A1A2E"
POPUP_BORDER_COLOR = "#00D9A3"  # Teal (ghost color)
POPUP_FG = "#FFFFFF"
POPUP_FONT_FAMILY = "Segoe UI"
POPUP_FONT_SIZE = 11
POPUP_ARROW_COLOR = "#00D9A3"


class PopupWindow:
    """A styled popup tooltip at a screen position."""

    def __init__(self, root: tk.Tk, x_px: int, y_px: int, text: str):
        self._win = tk.Toplevel(root)
        self._win.overrideredirect(True)
        self._win.attributes("-topmost", True)

        # Outer frame (acts as border)
        outer = tk.Frame(self._win, bg=POPUP_BORDER_COLOR, padx=2, pady=2)
        outer.pack()

        # Inner frame with content
        inner = tk.Frame(outer, bg=POPUP_BG, padx=10, pady=6)
        inner.pack()

        # Icon + text
        label = tk.Label(
            inner,
            text=f"👆 {text}",
            font=(POPUP_FONT_FAMILY, POPUP_FONT_SIZE),
            fg=POPUP_FG,
            bg=POPUP_BG,
        )
        label.pack()

        # Position: center above the target point
        self._win.update_idletasks()
        w = self._win.winfo_width()
        h = self._win.winfo_height()
        pos_x = x_px - w // 2
        pos_y = y_px - h - 15  # Above the target

        # Keep on screen
        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()
        pos_x = max(5, min(pos_x, screen_w - w - 5))
        pos_y = max(5, min(pos_y, screen_h - h - 5))

        self._win.geometry(f"+{pos_x}+{pos_y}")

        # Fade in effect (start transparent, go opaque)
        self._win.attributes("-alpha", 0.0)
        self._fade_in(0.0)

    def _fade_in(self, alpha: float):
        """Animate fade in."""
        if alpha < 0.95:
            self._win.attributes("-alpha", alpha)
            self._win.after(30, lambda: self._fade_in(alpha + 0.15))
        else:
            self._win.attributes("-alpha", 0.95)

    def destroy(self):
        try:
            self._win.destroy()
        except Exception:
            pass


class MarkerWindow:
    """A pulsing ring marker at the exact target position."""

    def __init__(self, root: tk.Tk, x_px: int, y_px: int):
        self._win = tk.Toplevel(root)
        self._win.overrideredirect(True)
        self._win.attributes("-topmost", True)
        self._win.attributes("-alpha", 0.85)

        size = 40
        canvas = tk.Canvas(
            self._win, width=size, height=size,
            bg="white", highlightthickness=0,
        )
        canvas.pack()

        # Make white transparent
        self._win.attributes("-transparentcolor", "white")

        # Draw teal ring
        pad = 4
        canvas.create_oval(
            pad, pad, size - pad, size - pad,
            outline=POPUP_BORDER_COLOR, width=3,
        )
        # Center dot
        cx, cy = size // 2, size // 2
        canvas.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, fill=POPUP_BORDER_COLOR, outline="")

        # Position centered on target
        pos_x = x_px - size // 2
        pos_y = y_px - size // 2
        self._win.geometry(f"{size}x{size}+{pos_x}+{pos_y}")

    def destroy(self):
        try:
            self._win.destroy()
        except Exception:
            pass


class ScreenOverlay:
    """
    Manages popup hint windows at screen positions.

    Runs a hidden Tkinter root in a background thread.
    """

    def __init__(self):
        self._root: Optional[tk.Tk] = None
        self._thread: Optional[threading.Thread] = None
        self._ready = threading.Event()
        self._popups: list = []
        self._screen_width = 0
        self._screen_height = 0

    def start(self):
        """Start the overlay manager in a background thread."""
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=3)

    def stop(self):
        """Stop and close all popups."""
        self.clear_popups()
        if self._root:
            try:
                self._root.after(0, self._root.quit)
            except Exception:
                pass

    def _run(self):
        """Tkinter main loop (hidden root, only Toplevels are visible)."""
        self._root = tk.Tk()
        self._root.withdraw()
        self._screen_width = self._root.winfo_screenwidth()
        self._screen_height = self._root.winfo_screenheight()
        self._ready.set()
        self._root.mainloop()

    def show_popup(self, x: float, y: float, text: str, color: str = POPUP_BG):
        """
        Show a popup label at normalized coordinates.

        Args:
            x: Horizontal position (0.0=left, 1.0=right)
            y: Vertical position (0.0=top, 1.0=bottom)
            text: Label text
        """
        if not self._root:
            return

        px = int(x * self._screen_width)
        py = int(y * self._screen_height)

        def _create():
            popup = PopupWindow(self._root, px, py, text)
            self._popups.append(popup)

        self._root.after(0, _create)

    def show_arrow(self, x: float, y: float, color: str = POPUP_ARROW_COLOR):
        """
        Show a marker ring at the target position.
        """
        if not self._root:
            return

        px = int(x * self._screen_width)
        py = int(y * self._screen_height)

        def _create():
            marker = MarkerWindow(self._root, px, py)
            self._popups.append(marker)

        self._root.after(0, _create)

    def clear_popups(self):
        """Remove all active popups."""
        if not self._root:
            return

        def _clear():
            for popup in self._popups:
                popup.destroy()
            self._popups.clear()

        self._root.after(0, _clear)
