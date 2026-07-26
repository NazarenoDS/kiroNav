"""
KiroNav Screen Overlay — Floating tooltip hints

Shows a tooltip with an arrow pointing toward the general area
where the user should look. Not pixel-precise — just directional guidance.
"""

import sys
import threading
from typing import Optional

if sys.platform != "win32":
    raise ImportError("screen_overlay is Windows-only")

import tkinter as tk
import tkinter.font as tkfont

# Style
BG_COLOR = "#1A1A2E"
BORDER_COLOR = "#00D9A3"
TEXT_COLOR = "#FFFFFF"
ARROW_COLOR = "#00D9A3"
FONT_FAMILY = "Segoe UI"
FONT_SIZE = 12


class ScreenOverlay:
    """
    Shows a floating tooltip near the target area with a directional arrow.
    Uses Tkinter Toplevel windows (no fullscreen, no click-through issues).
    """

    def __init__(self):
        self._root: Optional[tk.Tk] = None
        self._thread: Optional[threading.Thread] = None
        self._ready = threading.Event()
        self._tooltip: Optional[tk.Toplevel] = None
        self._screen_width = 0
        self._screen_height = 0

    def start(self):
        """Start the overlay manager."""
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=3)

    def stop(self):
        """Stop overlay."""
        self.clear_popups()
        if self._root:
            try:
                self._root.after(0, self._root.quit)
            except Exception:
                pass

    def _run(self):
        """Hidden Tkinter root in background thread."""
        # Enable DPI awareness so coordinates match the real screen resolution
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass

        self._root = tk.Tk()
        self._root.withdraw()
        self._screen_width = self._root.winfo_screenwidth()
        self._screen_height = self._root.winfo_screenheight()
        print(f"[Overlay] Screen: {self._screen_width}x{self._screen_height}")
        self._ready.set()
        self._root.mainloop()

    def show_popup(self, x: float, y: float, text: str, color: str = BG_COLOR):
        """
        Show a tooltip near the target area.

        Args:
            x: Approximate horizontal zone (0.0=left, 1.0=right)
            y: Approximate vertical zone (0.0=top, 1.0=bottom)
            text: Short label
        """
        if not self._root:
            return

        px = int(x * self._screen_width)
        py = int(y * self._screen_height)

        def _create():
            self._destroy_tooltip()

            tip = tk.Toplevel(self._root)
            tip.overrideredirect(True)
            tip.attributes("-topmost", True)
            tip.attributes("-alpha", 0.92)
            tip.configure(bg=BORDER_COLOR)

            # Main frame (border effect via padding)
            frame = tk.Frame(tip, bg=BG_COLOR, padx=12, pady=8)
            frame.pack(padx=2, pady=2)

            # Arrow character + text
            arrow_char = self._get_arrow_char(y)
            display_text = f"{arrow_char}  {text}"

            label = tk.Label(
                frame,
                text=display_text,
                font=(FONT_FAMILY, FONT_SIZE),
                fg=TEXT_COLOR,
                bg=BG_COLOR,
            )
            label.pack()

            # Position the tooltip OFFSET from target (not on top of it)
            tip.update_idletasks()
            w = tip.winfo_width()
            h = tip.winfo_height()

            # Place tooltip offset: above if target is low, below if high
            if y > 0.7:
                # Target is near bottom — show tooltip above
                pos_y = py - h - 40
            else:
                # Target is elsewhere — show tooltip below
                pos_y = py + 30

            # Horizontal: center on x but keep on screen
            pos_x = px - w // 2
            pos_x = max(10, min(pos_x, self._screen_width - w - 10))
            pos_y = max(10, min(pos_y, self._screen_height - h - 10))

            tip.geometry(f"+{pos_x}+{pos_y}")
            self._tooltip = tip

        self._root.after(0, _create)

    def show_arrow(self, x: float, y: float, color: str = ARROW_COLOR):
        """No-op — the tooltip already has directional arrows."""
        pass

    def clear_popups(self):
        """Remove the active tooltip."""
        if not self._root:
            return
        self._root.after(0, self._destroy_tooltip)

    def _destroy_tooltip(self):
        """Destroy current tooltip if any."""
        if self._tooltip:
            try:
                self._tooltip.destroy()
            except Exception:
                pass
            self._tooltip = None

    @staticmethod
    def _get_arrow_char(y: float) -> str:
        """Get a directional arrow based on vertical position."""
        if y > 0.8:
            return "👇"  # pointing down (target is below)
        elif y < 0.2:
            return "👆"  # pointing up (target is above)
        else:
            return "👉"  # pointing right (general)
