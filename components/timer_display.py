"""Timer display with countdown, editable input, and color state."""

from __future__ import annotations

import asyncio

import flet as ft


class TimerDisplay(ft.Container):

    """Shows an editable MM:SS input (idle) or countdown display (active).

    - Idle: editable text field for MM:SS input.
    - Running: monospace countdown display with color changes.
    - Last 60 seconds: orange, last 10: red.
    - Paused: amber + blinking.
    - Completed: green.
    """

    def __init__(self) -> None:
        self._remaining = 0
        self._is_paused = False
        self._blinking = False

        # ── Countdown display label ──────────────────────────
        self._label = ft.Text(
            "25:00",
            size=36,
            weight=ft.FontWeight.W_700,
            font_family="monospace",
            color=ft.Colors.WHITE,
            text_align=ft.TextAlign.CENTER,
        )

        # ── Editable input field (shown when idle) ───────────
        self._input_field = ft.TextField(
            hint_text="MM:SS",
            value="25:00",
            width=160,
            text_align=ft.TextAlign.CENTER,
            keyboard_type=ft.KeyboardType.NUMBER,
            border=ft.InputBorder.NONE,
            text_size=28,
            max_length=5,
            dense=True,
            content_padding=ft.Padding.symmetric(vertical=4, horizontal=8),
            bgcolor=ft.Colors.GREY_800,
        )

        # ── Status text ──────────────────────────────────────
        self._state_text = ft.Text(
            "Set time and press Start",
            size=12,
            color=ft.Colors.GREY_500,
            text_align=ft.TextAlign.CENTER,
        )

        # Container that swaps between input and label
        self._display_container = ft.Container(
            content=self._input_field,
            height=46,
        )

        super().__init__(
            bgcolor=ft.Colors.GREY_900,
            border_radius=12,
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
            content=ft.Column(
                controls=[self._display_container, self._state_text],
                spacing=2,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
            ),
        )

    # ── Input parsing ────────────────────────────────────────

    def get_input_seconds(self) -> int:
        """Parse input field to total seconds (max 359999)."""
        text = (self._input_field.value or "").strip()
        if not text:
            return 0
        if ":" in text:
            parts = text.split(":")
            if len(parts) == 2:
                try:
                    return min(int(parts[0]) * 60 + int(parts[1]), 359999)
                except ValueError:
                    return 0
        try:
            return min(int(text), 359999)
        except ValueError:
            return 0

    def validate_input(self) -> tuple[bool, str]:
        """Validate the input field. Returns (is_valid, error_message)."""
        text = (self._input_field.value or "").strip()
        if not text:
            return False, "Enter a time"
        if ":" in text:
            parts = text.split(":")
            if len(parts) != 2:
                return False, "Use MM:SS format"
            try:
                m, s = int(parts[0]), int(parts[1])
            except ValueError:
                return False, "Enter valid numbers"
            if m < 0 or s < 0:
                return False, "No negative values"
            if s >= 60:
                return False, "Seconds must be < 60"
            if m * 60 + s < 1:
                return False, "Minimum 1 second"
            if m * 60 + s > 359999:
                return False, "Max 99:59:59"
        else:
            try:
                val = int(text)
            except ValueError:
                return False, "Enter a valid number"
            if val < 1:
                return False, "Minimum 1 second"
            if val > 359999:
                return False, "Max 359999 seconds"
        return True, ""

    def set_input_from_seconds(self, total_seconds: int) -> None:
        """Set the input field from total seconds (MM:SS format)."""
        total_seconds = max(0, min(total_seconds, 359999))
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        if minutes >= 60:
            hours = minutes // 60
            minutes %= 60
            self._input_field.value = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            self._input_field.value = f"{minutes:02d}:{seconds:02d}"
        self._input_field.update()

    # ── Display mode switching ─────────────────────────────

    def show_idle(self) -> None:
        """Show editable input field."""
        self._remaining = 0
        self._is_paused = False
        self._stop_blinking()
        self._display_container.content = self._input_field
        self._state_text.value = "Set time and press Start"
        self._state_text.color = ft.Colors.GREY_500
        self.opacity = 1.0
        self.update()

    def update_display(self, remaining_seconds: int, is_paused: bool = False) -> None:
        """Update the countdown display with remaining time."""
        self._remaining = remaining_seconds
        self._is_paused = is_paused

        self._display_container.content = self._label

        hours = remaining_seconds // 3600
        minutes = (remaining_seconds % 3600) // 60
        seconds = remaining_seconds % 60

        if hours > 0:
            self._label.value = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            self._label.value = f"{minutes:02d}:{seconds:02d}"

        if is_paused:
            self._label.color = ft.Colors.AMBER_400
            self._state_text.value = "Paused"
            self._state_text.color = ft.Colors.AMBER_400
            self._start_blinking()
        else:
            self._stop_blinking()
            if remaining_seconds <= 10:
                self._label.color = ft.Colors.RED_400
                self._state_text.value = "Finishing..."
                self._state_text.color = ft.Colors.RED_400
            elif remaining_seconds <= 60:
                self._label.color = ft.Colors.ORANGE_400
                self._state_text.value = ""
            else:
                self._label.color = ft.Colors.WHITE
                self._state_text.value = ""

        self.update()

    def show_completed(self) -> None:
        """Indicate that the timer finished."""
        self._remaining = 0
        self._is_paused = False
        self._stop_blinking()
        self._display_container.content = self._label
        self._label.value = "00:00"
        self._label.color = ft.Colors.GREEN_400
        self._state_text.value = "Completed"
        self._state_text.color = ft.Colors.GREEN_400
        self.opacity = 1.0
        self.update()

    # ── Blinking animation (paused state) ─────────────────

    def _start_blinking(self) -> None:
        if self._blinking:
            return
        self._blinking = True
        asyncio.create_task(self._blink_loop())

    def _stop_blinking(self) -> None:
        self._blinking = False
        self.opacity = 1.0

    async def _blink_loop(self) -> None:
        low_opacity = True
        while self._blinking and self._is_paused:
            self.opacity = 0.4 if low_opacity else 1.0
            self.update()
            low_opacity = not low_opacity
            await asyncio.sleep(0.6)
