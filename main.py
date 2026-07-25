"""
KiroNav - Main Application

AI-powered software navigation assistant using Kiro CLI as backend.
"""

import os
import tempfile
from typing import Optional

import flet as ft
from dotenv import load_dotenv

from core.kiro_cli_backend import KiroCLIBackend, GuideResponse
from core.screen_capture import ScreenCapture, ScreenCaptureError
from ui.ghost import Ghost, GhostState
from ui.guide_panel import GuidePanel
from ui.overlay_renderer import OverlayRenderer
from ui.speech_bubble import SpeechBubble

load_dotenv()

PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")
SYSTEM_PROMPT_PATH = os.path.join(PROMPTS_DIR, "kiro_system_prompt.txt")
SCREENSHOT_PATH = os.path.join(tempfile.gettempdir(), "kironav_screenshot.png")

# Floating widget size. Tall and narrow so it sits at the edge of the screen.
WINDOW_WIDTH = 400
WINDOW_HEIGHT = 640

GHOST_SIZE = 120

NEXT_STEP_HINT = "Click el fantasma para el siguiente paso"


class KiroNavApp:
    """
    Main KiroNav application.

    Coordinates:
    - Ghost character (idle, watch, speak, happy)
    - Speech bubble (user input / AI output)
    - Guide panel (steps)
    - Overlay renderer (highlights, arrows)
    - Kiro CLI backend (AI inference)
    """

    def __init__(self):
        self.page: Optional[ft.Page] = None
        self.ghost: Optional[Ghost] = None
        self.speech_bubble: Optional[SpeechBubble] = None
        self.guide_panel: Optional[GuidePanel] = None
        self.overlay_renderer: Optional[OverlayRenderer] = None

        self.backend = KiroCLIBackend()
        self.screen_capture = ScreenCapture()

        self._processing = False
        self._system_prompt = ""

        # Current guide state
        self._task = ""
        self._steps: list[str] = []
        self._current_step = 0

    # ------------------------------------------------------------------ setup

    def main(self, page: ft.Page):
        """Main Flet entry point."""
        self.page = page

        page.title = "KiroNav"
        page.padding = 0

        # Transparent floating widget: no frame, no background, above other windows.
        page.bgcolor = ft.Colors.TRANSPARENT
        page.window.bgcolor = ft.Colors.TRANSPARENT
        page.window.frameless = True
        page.window.always_on_top = True
        page.window.width = WINDOW_WIDTH
        page.window.height = WINDOW_HEIGHT
        page.window.resizable = False

        if os.path.exists(SYSTEM_PROMPT_PATH):
            with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
                self._system_prompt = f.read()

        self._setup_ui()

        print(f"[KiroNav] Ready. Capture backend: {self.screen_capture.backend}")
        print("[KiroNav] Click the ghost to start.")

    def _setup_ui(self):
        """Set up the UI layout."""
        self.ghost = Ghost(size=GHOST_SIZE, initial_state=GhostState.IDLE)
        self.speech_bubble = SpeechBubble(on_submit=self._on_submit)
        self.guide_panel = GuidePanel()
        self.overlay_renderer = OverlayRenderer(self.page)

        ghost_button = ft.Container(
            content=self.ghost,
            width=GHOST_SIZE,
            height=GHOST_SIZE,
            on_click=self._on_ghost_click,
            tooltip="KiroNav",
        )

        # Panel and bubble stack above the ghost, all aligned to the right edge.
        widget_column = ft.Column(
            controls=[
                self.guide_panel,
                self.speech_bubble,
                ghost_button,
            ],
            spacing=10,
            alignment=ft.MainAxisAlignment.END,
            horizontal_alignment=ft.CrossAxisAlignment.END,
            expand=True,
        )

        self.page.add(
            ft.Stack(
                expand=True,
                controls=[
                    # Overlay layer sits below the widget so it never steals clicks.
                    self.overlay_renderer.layer,
                    ft.Container(
                        content=widget_column,
                        padding=10,
                        expand=True,
                    ),
                ],
            )
        )

        self.ghost.pulse()

    # --------------------------------------------------------------- handlers

    async def _on_ghost_click(self, e):
        """Ghost click: advance the guide if one is active, otherwise ask for input."""
        if self._processing:
            return

        if self._steps and self._current_step < len(self._steps):
            await self._advance_step()
            return

        if self.speech_bubble.visible:
            await self.speech_bubble.hide()
            self.ghost.set_state(GhostState.IDLE)
        else:
            self.speech_bubble.set_ready()
            self.speech_bubble.show()
            self.ghost.set_state(GhostState.WATCH)
            self.speech_bubble.focus_input()

    async def _on_submit(self, text: str):
        """User asked for something: capture the screen and ask Kiro CLI."""
        if self._processing or not text.strip():
            return

        self._task = text.strip()
        self._reset_guide()

        # A fresh request starts a fresh conversation.
        self.backend.reset_session()

        response = await self._ask(
            lambda path: self.backend.ask(
                self._task,
                screenshot_path=path,
                system_context=self._system_prompt,
            )
        )
        if response is not None:
            self._render_response(response)

    async def _advance_step(self):
        """Mark the current step done and ask for the next one."""
        self.guide_panel.mark_step_completed(self._current_step + 1)
        self._current_step += 1

        if self._current_step >= len(self._steps):
            response = await self._ask(
                lambda path: self.backend.next_step(
                    screenshot_path=path,
                    task=self._task,
                    current_step=self._current_step,
                    total_steps=len(self._steps),
                )
            )
            if response is not None:
                self._render_response(response)
        else:
            self.guide_panel.set_progress_hint(NEXT_STEP_HINT)

    # ------------------------------------------------------------------ logic

    async def _ask(self, call) -> Optional[GuideResponse]:
        """
        Capture the screen, run `call(screenshot_path)` and handle failures.

        Args:
            call: Coroutine function taking the screenshot path

        Returns:
            The GuideResponse, or None if the turn failed.
        """
        self._processing = True
        self.ghost.set_state(GhostState.WATCH)
        self.speech_bubble.set_loading()
        self.speech_bubble.show()

        try:
            print("[KiroNav] Capturing screen...")
            try:
                path = await self.screen_capture.save_frame(SCREENSHOT_PATH)
            except ScreenCaptureError as e:
                self._show_message(f"No pude ver tu pantalla.\n\n{e}")
                return None

            print(f"[KiroNav] Screenshot: {path}")
            self.ghost.set_state(GhostState.SPEAK)

            response = await call(path)

            if not response.ok:
                self._show_message(response.error)
                return None

            return response

        except Exception as e:  # noqa: BLE001 - surface any failure to the user
            print(f"[KiroNav] Error: {e}")
            self._show_message(f"Error: {e}")
            return None

        finally:
            self._processing = False
            self.page.update()

    def _render_response(self, response: GuideResponse):
        """Show a guide response in the panel, or as text if it has no steps."""
        if response.done:
            self._reset_guide()
            self.ghost.set_state(GhostState.HAPPY)
            self.guide_panel.show_completion(response.summary or "¡Listo!")
            self.speech_bubble.set_ready()
            return

        if not response.steps:
            self.ghost.set_state(GhostState.SPEAK)
            self._show_message(response.as_text())
            return

        self._steps = response.steps
        self._current_step = 0

        self.guide_panel.set_tutorial(
            title=response.summary or self._task,
            steps=response.steps,
        )
        self.guide_panel.set_progress_hint(NEXT_STEP_HINT)
        self.speech_bubble.set_ready()
        self.ghost.set_state(GhostState.WATCH)

    def _reset_guide(self):
        """Clear the active guide state."""
        self._steps = []
        self._current_step = 0

    def _show_message(self, text: str):
        """Show a plain message in the speech bubble."""
        self.speech_bubble.set_text(text)
        self.speech_bubble.show()
        self.ghost.set_state(GhostState.IDLE)


app = KiroNavApp()


def main():
    """Entry point."""
    ft.run(app.main)


if __name__ == "__main__":
    main()
