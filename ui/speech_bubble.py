"""
KiroNav Speech Bubble

Displays text input from user and responses from AI.
"""

import asyncio
from typing import Callable, Optional

import flet as ft

FADE_MS = 300


class SpeechBubble(ft.Container):
    """
    Speech bubble for user input and AI responses.

    Features:
    - Rounded bubble next to the ghost
    - Text input field with submit button
    - Animated show/hide
    - Loading state
    """

    def __init__(
        self,
        width: int = 350,
        height: int = 180,
        on_submit: Optional[Callable] = None,
    ):
        """
        Initialize speech bubble.

        Args:
            width: Bubble width
            height: Bubble height
            on_submit: Async callback invoked with the submitted text
        """
        self._on_submit = on_submit
        self._is_response = False

        # Text field
        self._text_field = ft.TextField(
            hint_text="¿En qué te puedo ayudar?",
            multiline=True,
            min_lines=2,
            max_lines=4,
            text_size=14,
            border_color=ft.Colors.with_opacity(0.3, ft.Colors.WHITE),
            focused_border_color=ft.Colors.WHITE,
            cursor_color=ft.Colors.WHITE,
            color=ft.Colors.WHITE,
            hint_style=ft.TextStyle(
                color=ft.Colors.with_opacity(0.5, ft.Colors.WHITE)
            ),
            content_padding=15,
            border_radius=15,
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.BLACK),
            on_submit=self._handle_submit,
        )

        # Submit button
        self._submit_btn = ft.IconButton(
            icon=ft.Icons.SEND_ROUNDED,
            icon_color=ft.Colors.WHITE,
            icon_size=20,
            tooltip="Enviar",
            on_click=self._handle_submit,
        )

        self._input_row = ft.Row(
            controls=[
                ft.Container(content=self._text_field, expand=True),
                self._submit_btn,
            ],
            spacing=5,
            vertical_alignment=ft.CrossAxisAlignment.END,
        )

        # Response display (for showing AI output)
        self._response_text = ft.Text(
            value="",
            size=13,
            color=ft.Colors.WHITE,
            selectable=True,
            expand=True,
        )

        # Held as an attribute so visibility is never toggled by list index.
        self._response_container = ft.Container(
            content=ft.Column(
                controls=[self._response_text],
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
            visible=False,
            expand=True,
        )

        # Loading indicator
        self._loading = ft.ProgressRing(
            width=20,
            height=20,
            stroke_width=2,
            color=ft.Colors.WHITE,
            visible=False,
        )

        super().__init__(
            width=width,
            height=height,
            bgcolor=ft.Colors.with_opacity(0.92, "#1A1A2E"),
            border_radius=20,
            border=ft.Border.all(2, ft.Colors.with_opacity(0.3, ft.Colors.WHITE)),
            padding=15,
            content=ft.Column(
                controls=[
                    self._input_row,
                    self._response_container,
                    self._loading,
                ],
                spacing=10,
                expand=True,
            ),
            opacity=0,
            animate_opacity=FADE_MS,
            visible=False,
        )

    # --------------------------------------------------------------- handlers

    async def _handle_submit(self, e):
        """Submit the current text (Enter key or send button)."""
        text = self.get_text()
        if text.strip() and self._on_submit:
            await self._on_submit(text)

    # ------------------------------------------------------------ visibility

    def show(self):
        """Show the speech bubble."""
        self.visible = True
        self.opacity = 1
        self.update()

    async def hide(self):
        """Fade out and hide the speech bubble."""
        self.opacity = 0
        self.update()
        await asyncio.sleep(FADE_MS / 1000)
        self.visible = False
        self.update()

    # ----------------------------------------------------------------- state

    def get_text(self) -> str:
        """Get current input text."""
        return self._text_field.value or ""

    def set_text(self, text: str):
        """Show an AI response instead of the input row."""
        self._is_response = True
        self._input_row.visible = False
        self._loading.visible = False
        self._response_text.value = text
        self._response_container.visible = True
        self.update()

    def set_loading(self):
        """Show the loading state."""
        self._is_response = False
        self._input_row.visible = False
        self._response_container.visible = False
        self._loading.visible = True
        self.update()

    def set_ready(self):
        """Reset to the input state."""
        self._is_response = False
        self._input_row.visible = True
        self._text_field.hint_text = "¿En qué te puedo ayudar?"
        self._text_field.disabled = False
        self._text_field.value = ""
        self._response_text.value = ""
        self._response_container.visible = False
        self._loading.visible = False
        self.update()

    # Kept as an alias: `clear()` and `set_ready()` had identical behaviour.
    clear = set_ready

    def focus_input(self):
        """Focus the text field."""
        self._text_field.focus()
