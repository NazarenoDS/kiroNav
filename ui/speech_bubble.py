"""
KiroNav Speech Bubble

Displays text input from user and responses from AI.
"""

import flet as ft
from typing import Callable, Optional


class SpeechBubble(ft.Container):
    """
    Speech bubble for user input and AI responses.
    
    Features:
    - Rounded bubble with tail pointing to ghost
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
            on_submit: Async callback when user submits text
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
            on_focus=self._handle_focus,
        )
        
        # Submit button
        self._submit_btn = ft.IconButton(
            icon=ft.Icons.SEND_ROUNDED,
            icon_color=ft.Colors.WHITE,
            icon_size=20,
            tooltip="Enviar",
            on_click=self._handle_submit_click,
        )
        
        # Response display (for showing AI output)
        self._response_text = ft.Text(
            value="",
            size=13,
            color=ft.Colors.WHITE,
            selectable=True,
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
            bgcolor=ft.Colors.with_opacity(0.9, "#1A1A2E"),
            border_radius=20,
            border=ft.border.Border.all(2, ft.Colors.with_opacity(0.3, ft.Colors.WHITE)),
            padding=15,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Container(
                                content=self._text_field,
                                expand=True,
                            ),
                            self._submit_btn,
                        ],
                        spacing=5,
                        vertical_alignment=ft.CrossAxisAlignment.END,
                    ),
                    ft.Container(
                        content=self._response_text,
                        visible=False,
                    ),
                    self._loading,
                ],
                spacing=10,
                expand=True,
            ),
            opacity=0,
            animate_opacity=300,
            visible=False,
        )
    
    def _handle_submit(self, e):
        """Handle Enter key in text field."""
        import asyncio
        text = self.get_text()
        if text.strip() and self._on_submit:
            asyncio.create_task(self._on_submit(text))
    
    def _handle_submit_click(self, e):
        """Handle submit button click."""
        import asyncio
        text = self.get_text()
        if text.strip() and self._on_submit:
            asyncio.create_task(self._on_submit(text))
    
    def _handle_focus(self, e):
        """Handle focus on text field."""
        pass
    
    def show(self):
        """Show the speech bubble with animation."""
        self.visible = True
        self.opacity = 1
        self.update()
    
    def hide(self):
        """Hide the speech bubble with animation."""
        self.opacity = 0
        import asyncio
        asyncio.create_task(self._hide_after_delay())
    
    async def _hide_after_delay(self):
        """Hide after opacity animation completes."""
        import asyncio
        await asyncio.sleep(0.3)
        self.visible = False
        self.update()
    
    def get_text(self) -> str:
        """Get current input text."""
        return self._text_field.value or ""
    
    def set_text(self, text: str):
        """Set displayed text (response mode)."""
        self._is_response = True
        self._text_field.visible = False
        self._submit_btn.visible = False
        self._response_text.value = text
        self.content.controls[2].visible = True  # Response container
        self.update()
    
    def clear(self):
        """Clear and reset to input mode."""
        self._is_response = False
        self._text_field.visible = True
        self._submit_btn.visible = True
        self._text_field.value = ""
        self._response_text.value = ""
        self.content.controls[2].visible = False
        self._loading.visible = False
        self.update()
    
    def set_loading(self):
        """Show loading state."""
        self._text_field.hint_text = "Pensando..."
        self._text_field.disabled = True
        self._submit_btn.visible = False
        self._loading.visible = True
        self.update()
    
    def set_ready(self):
        """Reset to ready state."""
        self._is_response = False
        self._text_field.visible = True
        self._submit_btn.visible = True
        self._text_field.hint_text = "¿En qué te puedo ayudar?"
        self._text_field.disabled = False
        self._text_field.value = ""
        self._response_text.value = ""
        self.content.controls[2].visible = False
        self._loading.visible = False
        self.update()
