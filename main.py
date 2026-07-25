"""
KiroNav - Main Application

AI-powered software navigation assistant using Kiro CLI as backend.
"""

import asyncio
import os
import tempfile
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

import flet as ft

from core.screen_capture import ScreenCapture
from core.kiro_cli_backend import KiroCLIBackend
from ui.ghost import Ghost, GhostState
from ui.speech_bubble import SpeechBubble
from ui.guide_panel import GuidePanel
from ui.overlay_renderer import OverlayRenderer


# Load system prompt
PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")
SYSTEM_PROMPT_PATH = os.path.join(PROMPTS_DIR, "kiro_system_prompt.txt")


class KiroNavApp:
    """
    Main KiroNav application.
    
    Coordinates:
    - Ghost character (idle, watch, speak, happy)
    - Speech bubble (user input / AI output)
    - Guide panel (steps, todolist)
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
    
    def main(self, page: ft.Page):
        """Main Flet entry point."""
        self.page = page
        
        # Configure page
        page.title = "KiroNav"
        page.bgcolor = "#1A1A2E"
        page.window.width = 800
        page.window.height = 600
        page.window.opacity = 1.0
        page.window.always_on_top = True
        
        # Load system prompt
        if os.path.exists(SYSTEM_PROMPT_PATH):
            with open(SYSTEM_PROMPT_PATH, "r") as f:
                self._system_prompt = f.read()
        
        # Create UI components
        self._setup_ui()
        
        # Start connection when ready
        page.on_ready = self._on_ready
    
    def _setup_ui(self):
        """Set up the UI layout."""
        # Ghost character
        self.ghost = Ghost(size=120, initial_state=GhostState.IDLE)
        
        # Speech bubble with submit callback
        self.speech_bubble = SpeechBubble(on_submit=self._on_submit)
        
        # Guide panel
        self.guide_panel = GuidePanel()
        
        # Overlay renderer
        self.overlay_renderer = OverlayRenderer(self.page)
        
        # Main layout
        self.page.add(
            ft.Stack(
                controls=[
                    # Ghost in center
                    ft.Container(
                        content=self.ghost,
                        alignment=ft.alignment.Alignment.CENTER,
                        expand=True,
                        on_click=self._on_ghost_click,
                    ),
                    # Speech bubble (right of ghost)
                    ft.Container(
                        content=self.speech_bubble,
                        right=180,
                        top="50%",
                    ),
                    # Guide panel (right side)
                    ft.Container(
                        content=self.guide_panel,
                        right=20,
                        top=50,
                    ),
                    # Overlay layer
                    self.overlay_renderer.layer,
                ],
            )
        )
    
    async def _on_ready(self):
        """Called when Flet page is ready."""
        print("[KiroNav] App ready! Click the ghost to start.")
        self.ghost.pulse()
    
    def _on_ghost_click(self, e):
        """Handle ghost click - show speech bubble for input."""
        if self._processing:
            return
        
        if self.speech_bubble.visible:
            self.speech_bubble.hide()
            self.ghost.set_state(GhostState.IDLE)
        else:
            self.speech_bubble.show()
            self.speech_bubble.set_ready()
            self.ghost.set_state(GhostState.WATCH)
            
            # Focus the text field
            self.speech_bubble._text_field.focus()
    
    async def _on_submit(self, text: str):
        """Handle user submission - capture screen and ask Kiro."""
        if self._processing or not text.strip():
            return
        
        self._processing = True
        self.ghost.set_state(GhostState.WATCH)
        self.speech_bubble.set_loading()
        
        try:
            # Capture screenshot
            print("[KiroNav] Capturing screen...")
            screenshot_path = os.path.join(tempfile.gettempdir(), "kironav_screenshot.png")
            
            frame = await self.screen_capture.get_frame()
            if frame:
                import base64
                import io
                import PIL.Image
                
                img_bytes = base64.b64decode(frame['data'])
                img = PIL.Image.open(io.BytesIO(img_bytes))
                img.save(screenshot_path)
                print(f"[KiroNav] Screenshot saved: {screenshot_path}")
            
            # Ask Kiro CLI
            print(f"[KiroNav] Asking Kiro: {text}")
            self.ghost.set_state(GhostState.SPEAK)
            
            response = await self.backend.ask_with_screenshot(
                prompt=text,
                screenshot_path=screenshot_path,
                system_context=self._system_prompt,
            )
            
            print(f"[KiroNav] Response: {response[:100]}...")
            
            # Show response in speech bubble
            self.speech_bubble.set_text(response)
            self.speech_bubble.show()
            
            # Parse and show steps if response contains numbered list
            self._parse_steps(response)
            
        except Exception as e:
            print(f"[KiroNav] Error: {e}")
            self.speech_bubble.set_text(f"Error: {str(e)}")
        
        finally:
            self._processing = False
            self.ghost.set_state(GhostState.IDLE)
    
    def _parse_steps(self, response: str):
        """Parse step-by-step instructions from response."""
        import re
        
        # Find numbered steps
        step_pattern = re.compile(r'(\d+)[\.\)]\s*(.+?)(?=\n\d+[\.\)]|\n\n|$)', re.DOTALL)
        matches = step_pattern.findall(response)
        
        if len(matches) >= 2:
            steps = [m[1].strip() for m in matches]
            
            # Find task title (first line or "How to..." pattern)
            title_match = re.search(r'^(?:#+\s*)?(.+?)(?:\n|$)', response)
            title = title_match.group(1) if title_match else "Tutorial"
            
            self.guide_panel.set_tutorial(title=title, steps=steps)
            self.speech_bubble.hide()


# Create app instance
app = KiroNavApp()


def main():
    """Entry point."""
    ft.app(target=app.main)


if __name__ == "__main__":
    main()
