"""
KiroNav - Main Application

AI-powered software navigation assistant using Kiro Gateway as backend.
"""

import asyncio
import os
import tempfile
from typing import Optional

import flet as ft
from dotenv import load_dotenv

from core.kiro_backend import KiroBackend, GuideResponse, StepInfo
from core.screen_capture import ScreenCapture, ScreenCaptureError
from core.watchdog import Watchdog
from ui.ghost import Ghost, GhostState
from ui.guide_panel import GuidePanel
from ui.speech_bubble import SpeechBubble

load_dotenv()

PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")
SYSTEM_PROMPT_PATH = os.path.join(PROMPTS_DIR, "kiro_system_prompt.txt")
SCREENSHOT_PATH = os.path.join(tempfile.gettempdir(), "kironav_screenshot.png")

# Floating widget size
WINDOW_WIDTH = 340
WINDOW_HEIGHT = 460

GHOST_SIZE = 100

NEXT_STEP_HINT = "Click el fantasma o esperá que detecte tu avance"


class KiroNavApp:
    """
    Main KiroNav application.

    Coordinates:
    - Ghost character (idle, watch, speak, happy)
    - Speech bubble (user input / AI output)
    - Guide panel (steps)
    - Screen overlay (popups at x,y positions)
    - Watchdog (auto-advance detection)
    - Kiro Gateway backend (AI inference via HTTP)
    """

    def __init__(self):
        self.page: Optional[ft.Page] = None
        self.ghost: Optional[Ghost] = None
        self.speech_bubble: Optional[SpeechBubble] = None
        self.guide_panel: Optional[GuidePanel] = None

        # Backend config from env or defaults
        model = os.environ.get("KIRO_MODEL", "claude-sonnet-4-5")
        base_url = os.environ.get("KIRO_GATEWAY_URL", "http://localhost:8100/v1")
        api_key = os.environ.get("KIRO_API_KEY", "kironav-local-dev")

        self.backend = KiroBackend(model=model, base_url=base_url, api_key=api_key)
        self.screen_capture = ScreenCapture()
        self.watchdog = Watchdog(
            on_step_done=self._on_watchdog_step_done,
            on_stuck=self._on_watchdog_stuck,
        )

        # Overlay (initialized after page is ready)
        self._overlay = None

        self._processing = False
        self._system_prompt = ""

        # Current guide state
        self._task = ""
        self._steps: list[StepInfo] = []
        self._current_step = 0

    # ------------------------------------------------------------------ setup

    def main(self, page: ft.Page):
        """Main Flet entry point."""
        self.page = page

        page.title = "KiroNav"
        page.padding = 0
        page.window.icon = "icons/kironav.png"

        # Transparent floating widget — always on top, frameless
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
        self._start_overlay()

        print(f"[KiroNav] Ready. Model: {self.backend.model}")
        print(f"[KiroNav] Capture backend: {self.screen_capture.backend}")

    def _setup_ui(self):
        """Set up the UI layout."""
        self.ghost = Ghost(size=GHOST_SIZE, initial_state=GhostState.IDLE)
        self.speech_bubble = SpeechBubble(on_submit=self._on_submit)
        self.guide_panel = GuidePanel()

        ghost_button = ft.Container(
            content=self.ghost,
            width=GHOST_SIZE,
            height=GHOST_SIZE,
            on_click=self._on_ghost_click,
            tooltip="Click para interactuar",
        )

        # Ghost at top-right, drag area to its left
        ghost_row = ft.Row(
            controls=[
                ft.WindowDragArea(
                    content=ft.Container(height=50),
                    expand=True,
                ),
                ghost_button,
            ],
            alignment=ft.MainAxisAlignment.END,
            vertical_alignment=ft.CrossAxisAlignment.START,
            spacing=0,
        )

        # Content area
        content_area = ft.Column(
            controls=[
                self.guide_panel,
                self.speech_bubble,
            ],
            spacing=8,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

        widget_column = ft.Column(
            controls=[
                ghost_row,
                content_area,
            ],
            spacing=4,
            expand=True,
        )

        self.page.add(
            ft.Container(
                content=widget_column,
                padding=10,
                expand=True,
            )
        )

        self.ghost.pulse()

    def _start_overlay(self):
        """Start the screen overlay for popups."""
        try:
            from ui.screen_overlay import ScreenOverlay
            self._overlay = ScreenOverlay()
            self._overlay.start()
            print("[KiroNav] Screen overlay started")
        except ImportError:
            print("[KiroNav] Screen overlay not available (Windows only)")
            self._overlay = None
        except Exception as e:
            print(f"[KiroNav] Overlay failed to start: {e}")
            self._overlay = None

    # --------------------------------------------------------------- handlers

    async def _on_ghost_click(self, e):
        """Ghost click: advance steps, toggle input, or dismiss."""
        if self._processing:
            return

        # If guide panel shows completion, dismiss it
        if self.guide_panel.visible and not self._steps:
            await self.guide_panel.hide()
            self.ghost.set_state(GhostState.IDLE)
            return

        # If there are active steps, advance manually
        if self._steps and self._current_step < len(self._steps):
            self.watchdog.reset()
            await self._advance_step()
            return

        # Toggle input bubble
        if self.speech_bubble.visible:
            await self.speech_bubble.hide()
            self.ghost.set_state(GhostState.IDLE)
        else:
            self.speech_bubble.set_ready()
            self.speech_bubble.show()
            self.ghost.set_state(GhostState.WATCH)
            self.speech_bubble.focus_input()

    async def _on_submit(self, text: str):
        """User asked for something: capture screen and ask the model."""
        if self._processing or not text.strip():
            return

        self._task = text.strip()
        self._reset_guide()
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
        """Mark the current step done and move forward."""
        self.watchdog.stop()
        self._clear_overlay()

        self.guide_panel.mark_step_completed(self._current_step + 1)
        self._current_step += 1

        if self._current_step >= len(self._steps):
            # All steps done, ask model if there's more
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
            self._show_current_step_overlay()
            self._start_watchdog()
            self.guide_panel.set_progress_hint(NEXT_STEP_HINT)

    # ------------------------------------------------------------ watchdog

    async def _on_watchdog_step_done(self):
        """Watchdog detected the step was completed."""
        print("[KiroNav] Watchdog: step done detected!")
        if self._steps and self._current_step < len(self._steps):
            await self._advance_step()

    async def _on_watchdog_stuck(self):
        """Watchdog gave up — user is stuck or away. Offer help."""
        print("[KiroNav] Watchdog: user appears stuck/away")
        if self._steps and self._current_step < len(self._steps):
            step_text = self._steps[self._current_step].text
            self.speech_bubble.set_text(
                f"¿Te trabaste? El paso era:\n\n\"{step_text}\"\n\n"
                "Click el fantasma cuando quieras seguir."
            )
            self.speech_bubble.show()
        self.ghost.set_state(GhostState.IDLE)

    def _start_watchdog(self):
        """Start the watchdog for the current step."""
        if not self._steps or self._current_step >= len(self._steps):
            return

        current_step_text = self._steps[self._current_step].text
        print(f"[KiroNav] Watchdog started for step: {current_step_text[:50]}...")

        async def check_fn() -> bool:
            """Capture screen and ask model if step was done."""
            try:
                print("[Watchdog] Checking if step was completed...")
                path = await self.screen_capture.save_frame(SCREENSHOT_PATH)
                result = await self.backend.check_step_done(path, current_step_text)
                print(f"[Watchdog] Model says done={result}")
                return result
            except Exception as e:
                print(f"[Watchdog] Check error: {e}")
                return False

        self.watchdog.start(check_fn)

    # ---------------------------------------------------------------- overlay

    def _show_current_step_overlay(self):
        """Show a popup on the overlay for the current step."""
        if not self._steps or self._current_step >= len(self._steps):
            return

        step = self._steps[self._current_step]
        print(f"[KiroNav] Overlay: label='{step.label}' x={step.x} y={step.y} overlay={self._overlay is not None}")

        if self._overlay and step.label:
            self._overlay.clear_popups()
            self._overlay.show_popup(step.x, step.y, step.label)
            self._overlay.show_arrow(step.x, step.y)

    def _clear_overlay(self):
        """Remove all overlay popups."""
        if self._overlay:
            self._overlay.clear_popups()

    # ------------------------------------------------------------------ logic

    async def _ask(self, call) -> Optional[GuideResponse]:
        """Capture the screen, run the call, and handle failures."""
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

            print(f"[KiroNav] Screenshot saved: {path}")
            self.ghost.set_state(GhostState.SPEAK)

            response = await call(path)

            if not response.ok:
                self._show_message(response.error)
                return None

            return response

        except Exception as e:
            print(f"[KiroNav] Error: {e}")
            self._show_message(f"Error: {e}")
            return None

        finally:
            self._processing = False
            self.page.update()

    def _render_response(self, response: GuideResponse):
        """Show a guide response in the panel and overlay."""
        self.watchdog.stop()
        self._clear_overlay()

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
            steps=response.step_texts,
        )
        self.guide_panel.set_progress_hint(NEXT_STEP_HINT)
        self.speech_bubble.set_ready()
        self.ghost.set_state(GhostState.WATCH)

        # Show overlay for first step + start watchdog
        self._show_current_step_overlay()
        self._start_watchdog()

    def _reset_guide(self):
        """Clear the active guide state."""
        self.watchdog.stop()
        self._clear_overlay()
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
