"""Timer display with mono font and color state."""

from __future__ import annotations

import asyncio

import flet as ft


class TimerDisplay(ft.Container):

    """Shows HH:MM:SS with monospace font and color changes.

    - Normal running: white text on dark background.
    - Last 60 seconds: red text.
    - Last 5 minutes: orange text.
    - Paused: amber color + blinking animation.
    - Completed: green text.
    - Idle: grey placeholder.
    """

    def __init__(self) -> None:
        self._remaining = 0
        self._is_paused = False
        self._blinking = False

        self._label = ft.Text(

            "--:--:--",
            size=36,
            weight=ft.FontWeight.W_700,
            font_family="monospace",

            color=ft.Colors.GREY_500,
            text_align=ft.TextAlign.CENTER,
        )
        self._state_text = ft.Text(

            "No active timer",
            size=12,

            color=ft.Colors.GREY_500,
            text_align=ft.TextAlign.CENTER,
        )

        super().__init__(
            bgcolor=ft.Colors.GREY_900,
            border_radius=12,
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            animate_opacity=300,
            content=ft.Column(
                controls=[self._label, self._state_text],
                spacing=2,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
            ),
        )

    def update_display(self, remaining_seconds: int, is_paused: bool = False) -> None:
        """Update the displayed time and color based on remaining seconds."""

        self._remaining = remaining_seconds
        self._is_paused = is_paused

        hours = remaining_seconds // 3600
        minutes = (remaining_seconds % 3600) // 60
        seconds = remaining_seconds % 60
        self._label.value = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        if is_paused:
            self._label.color = ft.Colors.AMBER_400
            self._state_text.value = "Paused"

            self._start_blinking()
        else:

            self._stop_blinking()
            if remaining_seconds <= 60:
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

        self._remaining = 0
        self._is_paused = False
        self._stop_blinking()

        self._label.value = "00:00:00"
        self._label.color = ft.Colors.GREEN_400
        self._state_text.value = "Completed"
        self.opacity = 1.0
        self.update()

    def show_idle(self) -> None:
        """Show the idle placeholder."""

        self._remaining = 0
        self._is_paused = False
        self._stop_blinking()

        self._label.value = "--:--:--"
        self._label.color = ft.Colors.GREY_500
        self._state_text.value = "No active timer"
        self.opacity = 1.0
        self.update()

    # ── Blinking animation (paused state) ─────────────────

    def _start_blinking(self) -> None:
        """Start a soft blink loop when the timer is paused."""

        if self._blinking:
            return
        self._blinking = True
        asyncio.create_task(self._blink_loop())

    def _stop_blinking(self) -> None:
        """Stop the blinking animation and restore full opacity."""

        self._blinking = False
        self.opacity = 1.0

    async def _blink_loop(self) -> None:
        """Blink the display opacity between 0.4 and 1.0."""

        low_opacity = True
        while self._blinking and self._is_paused:
            self.opacity = 0.4 if low_opacity else 1.0
            self.update()
            low_opacity = not low_opacity
            await asyncio.sleep(0.6)
