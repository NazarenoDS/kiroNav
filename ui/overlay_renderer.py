"""
KiroNav Overlay Renderer

Renders visual overlays (highlights, arrows) on screen.
"""

import flet as ft
from typing import Optional


class Highlight(ft.Container):
    """A highlighted region on screen."""
    
    COLORS = {
        "red": ft.Colors.RED_400,
        "blue": ft.Colors.BLUE_400,
        "green": ft.Colors.GREEN_400,
        "yellow": ft.Colors.YELLOW_400,
        "orange": ft.Colors.ORANGE_400,
    }
    
    def __init__(
        self,
        x: float,  # Normalized 0-1
        y: float,
        width: float,
        height: float,
        color: str = "red",
        label: Optional[str] = None,
    ):
        """
        Initialize highlight.
        
        Args:
            x, y: Top-left corner (normalized 0-1)
            width, height: Size (normalized 0-1)
            color: Color name
            label: Optional text label
        """
        bg_color = self.COLORS.get(color, ft.Colors.RED_400)
        
        label_content = None
        if label:
            label_content = ft.Container(
                content=ft.Text(
                    label,
                    size=12,
                    color=ft.Colors.WHITE,
                    weight=ft.FontWeight.BOLD,
                ),
                bgcolor=bg_color,
                border_radius=5,
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                bottom=5,
                right=5,
            )
        
        super().__init__(
            # Position will be set by OverlayRenderer
            width=200,  # Placeholder, will be updated
            height=100,
            bgcolor=ft.Colors.with_opacity(0.3, bg_color),
            border=ft.border.Border.all(3, bg_color),
            border_radius=8,
            content=label_content,
            opacity=0,
            animate_opacity=200,
        )


class Arrow(ft.Container):
    """An arrow drawn between two points."""
    
    def __init__(
        self,
        from_x: float,
        from_y: float,
        to_x: float,
        to_y: float,
        color: str = "red",
    ):
        """
        Initialize arrow.
        
        Args:
            from_x, from_y: Start point (normalized 0-1)
            to_x, to_y: End point (normalized 0-1)
            color: Color name
        """
        # Arrow will be drawn using Canvas
        self._from_x = from_x
        self._from_y = from_y
        self._to_x = to_x
        self._to_y = to_y
        
        bg_color = Highlight.COLORS.get(color, ft.Colors.RED_400)
        
        super().__init__(
            content=ft.Canvas(
                shapes=[
                    ft.Line(
                        offset=ft.Offset(from_x * 800, from_y * 600),
                        color=bg_color,
                        width=3,
                    ),
                ],
            ),
            opacity=0,
            animate_opacity=200,
        )


class OverlayRenderer:
    """
    Manages visual overlays on the Flet page.
    
    Coordinates screen coordinates to Flet page coordinates.
    """
    
    def __init__(self, page: ft.Page):
        """
        Initialize overlay renderer.
        
        Args:
            page: Flet page to render overlays on
        """
        self._page = page
        self._overlays: list[ft.Control] = []
        self._overlay_layer = ft.Stack(
            expand=True,
            controls=[],
        )
    
    @property
    def layer(self) -> ft.Stack:
        """Get the overlay layer to add to page."""
        return self._overlay_layer
    
    def _add_overlay(self, overlay: ft.Control):
        """Add an overlay to the layer."""
        self._overlays.append(overlay)
        self._overlay_layer.controls.append(overlay)
        self._page.update()
    
    def _remove_overlay(self, overlay: ft.Control):
        """Remove an overlay from the layer."""
        if overlay in self._overlays:
            self._overlays.remove(overlay)
            self._overlay_layer.controls.remove(overlay)
            self._page.update()
    
    def clear_all(self):
        """Clear all overlays."""
        self._overlays.clear()
        self._overlay_layer.controls.clear()
        self._page.update()
    
    def highlight_region(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        color: str = "red",
        label: Optional[str] = None,
    ) -> Highlight:
        """
        Add a highlight overlay.
        
        Args:
            x, y: Top-left corner (normalized 0-1)
            width, height: Size (normalized 0-1)
            color: Color name
            label: Optional text label
            
        Returns:
            The created Highlight object
        """
        highlight = Highlight(
            x=x,
            y=y,
            width=width,
            height=height,
            color=color,
            label=label,
        )
        
        self._add_overlay(highlight)
        
        # Fade in
        highlight.opacity = 1
        self._page.update()
        
        return highlight
    
    def remove_highlight(self, highlight: Highlight):
        """Remove a highlight overlay."""
        highlight.opacity = 0
        self._page.update()
        
        import asyncio
        asyncio.create_task(self._remove_after_delay(highlight))
    
    async def _remove_after_delay(self, overlay: ft.Control):
        """Remove after animation completes."""
        import asyncio
        await asyncio.sleep(0.2)
        self._remove_overlay(overlay)
    
    def draw_arrow(
        self,
        from_x: float,
        from_y: float,
        to_x: float,
        to_y: float,
        color: str = "red",
    ) -> Arrow:
        """
        Draw an arrow between two points.
        
        Args:
            from_x, from_y: Start point (normalized 0-1)
            to_x, to_y: End point (normalized 0-1)
            color: Color name
            
        Returns:
            The created Arrow object
        """
        arrow = Arrow(
            from_x=from_x,
            from_y=from_y,
            to_x=to_x,
            to_y=to_y,
            color=color,
        )
        
        self._add_overlay(arrow)
        
        # Fade in
        arrow.opacity = 1
        self._page.update()
        
        return arrow
    
    def remove_arrow(self, arrow: Arrow):
        """Remove an arrow."""
        arrow.opacity = 0
        self._page.update()
        
        import asyncio
        asyncio.create_task(self._remove_after_delay(arrow))
