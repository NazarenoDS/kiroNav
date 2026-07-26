"""
KiroNav Ghost Character

Animated ghost character using SVG animations.
"""

import os
from enum import Enum
from typing import Optional

import flet as ft


class GhostState(Enum):
    """Ghost character states."""
    IDLE = "idle"
    WATCH = "watch"
    SPEAK = "speak"
    HAPPY = "happy"


class Ghost(ft.Image):
    """
    KiroNav ghost character.
    
    A teal ghost with animated eyes based on state.
    No mouth - expression through eye movement only.
    """
    
    # Ghost colors
    COLOR_PRIMARY = "#00D9A3"  # Teal
    COLOR_SECONDARY = "#00B386"  # Darker teal
    COLOR_EYES = "#FFFFFF"  # White eyes
    
    def __init__(
        self,
        size: int = 120,
        initial_state: GhostState = GhostState.IDLE,
    ):
        """
        Initialize ghost character.
        
        Args:
            size: Size in pixels (width and height)
            initial_state: Starting animation state
        """
        self.size = size
        self._state = initial_state
        self._asset_dir = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "assets", "ghost")
        )
        
        super().__init__(
            src=self._get_asset_path(initial_state),
            width=size,
            height=size,
            fit="contain",
            animate_opacity=300,
        )
    
    def _get_asset_path(self, state: GhostState) -> str:
        """Get SVG file path for state."""
        return os.path.join(self._asset_dir, f"{state.value}.svg")
    
    @property
    def state(self) -> GhostState:
        return self._state
    
    def set_state(self, state: GhostState):
        """
        Change ghost animation state.
        
        Args:
            state: New state (IDLE, WATCH, SPEAK, HAPPY)
        """
        self._state = state
        self.src = self._get_asset_path(state)
        self.update()
    
    def pulse(self):
        """Add a pulsing glow effect."""
        self.shadow = ft.BoxShadow(
            spread_radius=5,
            blur_radius=15,
            color=ft.Colors.with_opacity(0.5, self.COLOR_PRIMARY),
        )
        self.update()
    
    def stop_pulse(self):
        """Remove pulsing glow effect."""
        self.shadow = None
        self.update()
