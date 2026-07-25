"""
KiroNav Overlay Renderer

Renders visual overlays (highlights, arrows) on the KiroNav overlay layer.

Coordinates are normalized 0-1 against the overlay layer, so the same values work
regardless of window size. OverlayRenderer converts them to pixels before adding
a shape to the layer.
"""

import asyncio
import math
from typing import Optional

import flet as ft
import flet.canvas as cv

FADE_MS = 200

COLORS = {
    "red": ft.Colors.RED_400,
    "blue": ft.Colors.BLUE_400,
    "green": ft.Colors.GREEN_400,
    "yellow": ft.Colors.YELLOW_400,
    "orange": ft.Colors.ORANGE_400,
}

DEFAULT_COLOR = ft.Colors.RED_400


def _resolve_color(name: str) -> str:
    """Map a color name to a Flet color, falling back to red."""
    return COLORS.get(name, DEFAULT_COLOR)


class Highlight(ft.Container):
    """
    A highlighted region on the overlay layer.

    Normalized coordinates are kept on the instance; `place()` turns them into
    the absolute Stack position and pixel size.
    """

    def __init__(
        self,
        x: float,
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
        self.norm_x = x
        self.norm_y = y
        self.norm_width = width
        self.norm_height = height

        box_color = _resolve_color(color)

        label_content = None
        if label:
            label_content = ft.Container(
                content=ft.Text(
                    label,
                    size=12,
                    color=ft.Colors.WHITE,
                    weight=ft.FontWeight.BOLD,
                ),
                bgcolor=box_color,
                border_radius=5,
                padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                alignment=ft.Alignment.BOTTOM_RIGHT,
            )

        super().__init__(
            bgcolor=ft.Colors.with_opacity(0.25, box_color),
            border=ft.Border.all(3, box_color),
            border_radius=8,
            content=label_content,
            alignment=ft.Alignment.BOTTOM_RIGHT,
            opacity=0,
            animate_opacity=FADE_MS,
        )

    def place(self, layer_width: float, layer_height: float):
        """
        Convert normalized coordinates into absolute position and pixel size.

        Args:
            layer_width, layer_height: Size of the overlay layer in pixels
        """
        self.left = self.norm_x * layer_width
        self.top = self.norm_y * layer_height
        self.width = max(self.norm_width * layer_width, 1)
        self.height = max(self.norm_height * layer_height, 1)


class Arrow(ft.Container):
    """
    An arrow drawn between two normalized points.

    The container fills the overlay layer and draws the arrow on a canvas, so the
    line is not clipped by a bounding box.
    """

    HEAD_LENGTH = 16
    HEAD_ANGLE = math.radians(28)

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
        self.norm_from_x = from_x
        self.norm_from_y = from_y
        self.norm_to_x = to_x
        self.norm_to_y = to_y
        self._color = _resolve_color(color)

        self._canvas = cv.Canvas(shapes=[], expand=True)

        super().__init__(
            content=self._canvas,
            opacity=0,
            animate_opacity=FADE_MS,
        )

    def place(self, layer_width: float, layer_height: float):
        """
        Rebuild the arrow shapes for the current layer size.

        Args:
            layer_width, layer_height: Size of the overlay layer in pixels
        """
        self.left = 0
        self.top = 0
        self.width = layer_width
        self.height = layer_height

        x1 = self.norm_from_x * layer_width
        y1 = self.norm_from_y * layer_height
        x2 = self.norm_to_x * layer_width
        y2 = self.norm_to_y * layer_height

        paint = ft.Paint(color=self._color, stroke_width=3)
        shapes = [cv.Line(x1, y1, x2, y2, paint=paint)]

        # Arrow head: two short lines rotated off the incoming direction.
        angle = math.atan2(y2 - y1, x2 - x1)
        for offset in (self.HEAD_ANGLE, -self.HEAD_ANGLE):
            head_angle = angle + math.pi - offset
            shapes.append(
                cv.Line(
                    x2,
                    y2,
                    x2 + self.HEAD_LENGTH * math.cos(head_angle),
                    y2 + self.HEAD_LENGTH * math.sin(head_angle),
                    paint=paint,
                )
            )

        self._canvas.shapes = shapes


class OverlayRenderer:
    """
    Manages visual overlays on the KiroNav overlay layer.

    Converts normalized coordinates to the layer's pixel size and handles
    fade-in / fade-out.
    """

    # Used before the page reports a size.
    FALLBACK_SIZE = (800.0, 600.0)

    def __init__(self, page: ft.Page):
        """
        Initialize overlay renderer.

        Args:
            page: Flet page the overlay layer belongs to
        """
        self._page = page
        self._overlays: list[ft.Control] = []
        self._overlay_layer = ft.Stack(expand=True, controls=[])

    @property
    def layer(self) -> ft.Stack:
        """The overlay layer to add to the page."""
        return self._overlay_layer

    def _layer_size(self) -> tuple[float, float]:
        """Current layer size in pixels, falling back before first layout."""
        width = getattr(self._page, "width", None) or self.FALLBACK_SIZE[0]
        height = getattr(self._page, "height", None) or self.FALLBACK_SIZE[1]
        return float(width), float(height)

    def _add_overlay(self, overlay: ft.Control):
        """Place, add and fade in an overlay."""
        overlay.place(*self._layer_size())

        self._overlays.append(overlay)
        self._overlay_layer.controls.append(overlay)
        self._page.update()

        overlay.opacity = 1
        self._page.update()

    def _remove_overlay(self, overlay: ft.Control):
        """Remove an overlay from the layer immediately."""
        if overlay in self._overlays:
            self._overlays.remove(overlay)
            self._overlay_layer.controls.remove(overlay)
            self._page.update()

    async def _fade_out(self, overlay: ft.Control):
        """Fade an overlay out, then remove it."""
        overlay.opacity = 0
        self._page.update()
        await asyncio.sleep(FADE_MS / 1000)
        self._remove_overlay(overlay)

    def clear_all(self):
        """Clear all overlays."""
        self._overlays.clear()
        self._overlay_layer.controls.clear()
        self._page.update()

    def reflow(self):
        """Re-place every overlay after the window is resized."""
        size = self._layer_size()
        for overlay in self._overlays:
            overlay.place(*size)
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
            The created Highlight
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
        return highlight

    async def remove_highlight(self, highlight: Highlight):
        """Fade out and remove a highlight."""
        await self._fade_out(highlight)

    def draw_arrow(
        self,
        from_x: float,
        from_y: float,
        to_x: float,
        to_y: float,
        color: str = "red",
    ) -> Arrow:
        """
        Draw an arrow between two normalized points.

        Args:
            from_x, from_y: Start point (normalized 0-1)
            to_x, to_y: End point (normalized 0-1)
            color: Color name

        Returns:
            The created Arrow
        """
        arrow = Arrow(
            from_x=from_x,
            from_y=from_y,
            to_x=to_x,
            to_y=to_y,
            color=color,
        )
        self._add_overlay(arrow)
        return arrow

    async def remove_arrow(self, arrow: Arrow):
        """Fade out and remove an arrow."""
        await self._fade_out(arrow)
