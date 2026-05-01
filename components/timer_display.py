"""Timer display with mono font and color state."""

from __future__ import annotations

import flet as ft


class TimerDisplay(ft.Container):
    """Shows HH:MM:SS with monospace font and color changes."""

    def __init__(self) -> None:
        self._label = ft.Text(
            "00:00:00",
            size=36,
            weight=ft.FontWeight.W_700,
            font_family="monospace",
            color=ft.Colors.WHITE,
            text_align=ft.TextAlign.CENTER,
        )
        self._state_text = ft.Text(
            "",
            size=12,
            color=ft.Colors.GREY_400,
            text_align=ft.TextAlign.CENTER,
        )

        super().__init__(
            bgcolor=ft.Colors.GREY_900,
            border_radius=12,
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            content=ft.Column(
                controls=[self._label, self._state_text],
                spacing=2,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
            ),
        )

    def update_display(self, remaining_seconds: int, is_paused: bool = False) -> None:
        """Update the displayed time and color based on remaining seconds."""

        hours = remaining_seconds // 3600
        minutes = (remaining_seconds % 3600) // 60
        seconds = remaining_seconds % 60
        self._label.value = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        if is_paused:
            self._label.color = ft.Colors.AMBER_400
            self._state_text.value = "Paused"
        elif remaining_seconds <= 60:
            self._label.color = ft.Colors.RED_400
            self._state_text.value = "Finishing..."
        elif remaining_seconds <= 300:
            self._label.color = ft.Colors.ORANGE_400
            self._state_text.value = ""
        else:
            self._label.color = ft.Colors.WHITE
            self._state_text.value = ""

        self.update()

    def show_completed(self) -> None:
        """Indicate that the timer is done."""

        self._label.value = "00:00:00"
        self._label.color = ft.Colors.GREEN_400
        self._state_text.value = "Completed"
        self.update()

    def show_idle(self) -> None:
        """Show the idle placeholder."""

        self._label.value = "--:--:--"
        self._label.color = ft.Colors.GREY_500
        self._state_text.value = "No active timer"
        self.update()
