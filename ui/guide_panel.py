"""
KiroNav Guide Panel

Displays step-by-step instructions and todo lists.
"""

import asyncio

import flet as ft


class StepItem(ft.Container):
    """Single step in the guide."""
    
    def __init__(self, number: int, instruction: str, is_current: bool = False):
        self._number = number
        self._instruction = instruction
        self._is_current = is_current
        
        # Step number circle
        self._number_badge = ft.Container(
            width=28,
            height=28,
            border_radius=14,
            bgcolor=ft.Colors.WHITE if is_current else ft.Colors.with_opacity(0.3, ft.Colors.WHITE),
            alignment=ft.alignment.Alignment.CENTER,
            content=ft.Text(
                str(number),
                color="#1A1A2E" if is_current else ft.Colors.WHITE,
                size=12,
                weight=ft.FontWeight.BOLD,
            ),
        )
        
        # Instruction text
        self._text = ft.Text(
            instruction,
            size=13,
            color=ft.Colors.WHITE if is_current else ft.Colors.with_opacity(0.7, ft.Colors.WHITE),
            weight=ft.FontWeight.NORMAL if is_current else ft.FontWeight.W_300,
        )
        
        super().__init__(
            content=ft.Row(
                controls=[
                    self._number_badge,
                    ft.Container(
                        content=self._text,
                        expand=True,
                    ),
                ],
                spacing=10,
            ),
            padding=ft.Padding.symmetric(vertical=5, horizontal=10),
            border_radius=10,
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE) if is_current else None,
        )
    
    def mark_completed(self):
        """Mark step as completed."""
        self._number_badge.bgcolor = ft.Colors.GREEN
        self._number_badge.content = ft.Text("✓", color=ft.Colors.WHITE, size=12, weight=ft.FontWeight.BOLD)
        self._text.color = ft.Colors.with_opacity(0.5, ft.Colors.WHITE)
        self.update()
    
    def mark_current(self):
        """Mark step as current."""
        self._number_badge.bgcolor = ft.Colors.WHITE
        self._number_badge.content = ft.Text(str(self._number), color="#1A1A2E", size=12, weight=ft.FontWeight.BOLD)
        self._text.color = ft.Colors.WHITE
        self._text.weight = ft.FontWeight.NORMAL
        self.bgcolor = ft.Colors.with_opacity(0.1, ft.Colors.WHITE)
        self.update()


class GuidePanel(ft.Container):
    """
    Panel showing step-by-step instructions.
    
    Features:
    - Animated show/hide
    - Progress indicator
    - Scrollable step list
    """
    
    def __init__(
        self,
        width: int = 320,
    ):
        """
        Initialize guide panel.

        Args:
            width: Panel width
        """
        self._title = ft.Text(
            "",
            size=15,
            color=ft.Colors.WHITE,
            weight=ft.FontWeight.BOLD,
            max_lines=2,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        
        self._progress_text = ft.Text(
            "",
            size=12,
            color=ft.Colors.with_opacity(0.7, ft.Colors.WHITE),
        )
        
        # Shown under the step list, e.g. how to advance to the next step.
        self._hint_text = ft.Text(
            "",
            size=11,
            italic=True,
            color=ft.Colors.with_opacity(0.6, ft.Colors.WHITE),
            visible=False,
        )
        
        self._steps_list = ft.Column(
            spacing=5,
            scroll=ft.ScrollMode.AUTO,
        )
        
        super().__init__(
            width=width,
            max_height=300,
            bgcolor=ft.Colors.with_opacity(0.9, "#1A1A2E"),
            border_radius=15,
            border=ft.Border.all(1, ft.Colors.with_opacity(0.2, ft.Colors.WHITE)),
            padding=12,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Container(content=self._title, expand=True),
                            self._progress_text,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                    ft.Divider(color=ft.Colors.with_opacity(0.2, ft.Colors.WHITE)),
                    self._steps_list,
                    self._hint_text,
                ],
                spacing=8,
                tight=True,
            ),
            opacity=0,
            animate_opacity=300,
            visible=False,
        )
    
    def show(self):
        """Show the guide panel."""
        self.visible = True
        self.opacity = 1
        self.update()
    
    async def hide(self):
        """Fade out and hide the guide panel."""
        self.opacity = 0
        self.update()
        await asyncio.sleep(0.3)
        self.visible = False
        self.update()
    
    def set_tutorial(self, title: str, steps: list[str]):
        """
        Set a new tutorial with multiple steps.
        
        Args:
            title: Tutorial title
            steps: List of step instructions
        """
        self._title.value = title
        self._progress_text.value = f"0/{len(steps)}"
        
        self._steps_list.controls.clear()
        
        for i, step in enumerate(steps, 1):
            step_item = StepItem(
                number=i,
                instruction=step,
                is_current=(i == 1),
            )
            self._steps_list.controls.append(step_item)
        
        self.show()
    
    def set_step(self, number: int, instruction: str, total: int):
        """
        Set current step (simple single-step mode).
        
        Args:
            number: Current step number
            instruction: Step instruction
            total: Total steps
        """
        self._title.value = f"Paso {number}/{total}"
        self._progress_text.value = ""
        
        self._steps_list.controls.clear()
        
        step_item = StepItem(
            number=number,
            instruction=instruction,
            is_current=True,
        )
        self._steps_list.controls.append(step_item)
        
        self.show()
    
    def set_progress_hint(self, hint: str):
        """
        Set the hint line under the step list.
        
        Args:
            hint: Hint text; empty hides the line
        """
        self._hint_text.value = hint
        self._hint_text.visible = bool(hint)
        self.update()
    
    def mark_step_completed(self, step_number: int):
        """Mark a step as completed."""
        steps = [c for c in self._steps_list.controls if isinstance(c, StepItem)]
        
        if not 1 <= step_number <= len(steps):
            return
        
        steps[step_number - 1].mark_completed()
        
        # Mark next step as current
        if step_number < len(steps):
            steps[step_number].mark_current()
        
        self._progress_text.value = f"{step_number}/{len(steps)}"
        self.update()
    
    def show_completion(self, summary: str):
        """Show completion message."""
        self._title.value = "✅ ¡Completado!"
        self._progress_text.value = ""
        self.set_progress_hint("")
        
        self._steps_list.controls.clear()
        self._steps_list.controls.append(
            ft.Container(
                content=ft.Text(
                    summary,
                    size=13,
                    color=ft.Colors.WHITE,
                ),
                padding=10,
            )
        )
        
        self.show()
