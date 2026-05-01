"""Persistent timer widget shown as a side panel."""

from __future__ import annotations

import flet as ft

from api.timer_api import cancel_timer, pause_timer, resume_timer, start_timer
from components.timer_display import TimerDisplay
from state import ws_client
from state.app_state import app_state


class TimerWidget(ft.Container):
    """Side panel widget that shows and controls the active timer."""

    def __init__(self) -> None:
        self._timer_id: str | None = None
        self._task_id: str | None = None
        self._status: str = "idle"
        self._task_name: str = ""

        self._display = TimerDisplay()
        self._task_label = ft.Text(
            "",
            size=13,
            weight=ft.FontWeight.W_600,
            color=ft.Colors.WHITE,
            text_align=ft.TextAlign.CENTER,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        self._pause_btn = ft.Button(
            "Pause",
            icon=ft.Icons.PAUSE_CIRCLE_FILLED,
            visible=False,
            on_click=self._on_pause,
        )
        self._resume_btn = ft.Button(
            "Resume",
            icon=ft.Icons.PLAY_CIRCLE_FILLED,
            visible=False,
            on_click=self._on_resume,
        )
        self._cancel_btn = ft.Button(
            "Cancel",
            icon=ft.Icons.STOP_CIRCLE,
            visible=False,
            on_click=self._on_cancel,
        )
        self._start_without_task_btn = ft.Button(
            "Start timer",
            icon=ft.Icons.TIMER,
            visible=True,
            on_click=self._on_start_without_task,
        )

        button_row = ft.Row(
            controls=[self._pause_btn, self._resume_btn, self._cancel_btn],
            spacing=6,
            alignment=ft.MainAxisAlignment.CENTER,
        )

        super().__init__(
            bgcolor=ft.Colors.GREY_800,
            border_radius=12,
            padding=16,
            width=220,
            animate=ft.Animation(300, ft.AnimationCurve.EASE_IN_OUT),
            content=ft.Column(
                controls=[
                    ft.Text(
                        "Timer",
                        size=14,
                        weight=ft.FontWeight.W_700,
                        color=ft.Colors.GREY_300,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Container(height=8),
                    self._task_label,
                    ft.Container(height=8),
                    self._display,
                    ft.Container(height=8),
                    button_row,
                    self._start_without_task_btn,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
            ),
        )

        # Tick and finished are handled by ws_client directly.
        # The WS client updates the label text in-place every second
        # without touching this widget. On finished it shows a snackbar.

    def set_task_info(self, task_name: str, task_id: str | None = None) -> None:
        """Set the active task name shown in the widget."""

        self._task_name = task_name
        self._task_id = task_id
        self._update_task_display()

    def _update_task_display(self) -> None:
        """Update the task label visibility."""

        if self._task_name and self._status != "idle":
            self._task_label.value = self._task_name
            self._task_label.visible = True
        else:
            self._task_label.visible = False
        self.update()

    # ── Button handlers ──────────────────────────────────

    async def _on_start_without_task(self, _: ft.ControlEvent) -> None:
        """Start a timer without linking it to any task."""

        if not app_state.workspace_id:
            return

        try:
            result = await start_timer(
                workspace_id=app_state.workspace_id,
                estimated_seconds=0,
            )
            self._timer_id = result["id"]
            ws_client.set_active_timer_id(self._timer_id)
            self._status = "running"
            self._task_id = None
            self._task_name = "General"
            self._update_ui_state()
        except Exception:
            pass

    async def _on_pause(self, _: ft.ControlEvent) -> None:
        """Pause the active timer."""

        if not self._timer_id or not app_state.workspace_id:
            return

        try:
            await pause_timer(self._timer_id, app_state.workspace_id)
            self._status = "paused"
            self._update_ui_state()
        except Exception:
            pass

    async def _on_resume(self, _: ft.ControlEvent) -> None:
        """Resume the paused timer."""

        if not self._timer_id or not app_state.workspace_id:
            return

        try:
            await resume_timer(self._timer_id, app_state.workspace_id)
            self._status = "running"
            self._update_ui_state()
        except Exception:
            pass

    async def _on_cancel(self, _: ft.ControlEvent) -> None:
        """Cancel the active timer."""

        if not self._timer_id or not app_state.workspace_id:
            return

        try:
            await cancel_timer(self._timer_id, app_state.workspace_id)
            ws_client.set_active_timer_id(None)
            self._timer_id = None
            self._status = "idle"
            self._display.show_idle()
            self._update_ui_state()
        except Exception:
            pass

    def reset(self) -> None:
        """Reset the widget to idle state."""

        self._timer_id = None
        ws_client.set_active_timer_id(None)
        self._task_id = None
        self._status = "idle"
        self._task_name = ""
        self._display.show_idle()
        self._update_ui_state()

    def _update_ui_state(self) -> None:
        """Show/hide buttons based on the current timer status."""

        is_running = self._status == "running"
        is_paused = self._status == "paused"
        is_idle = self._status == "idle"
        is_completed = self._status == "completed"

        self._pause_btn.visible = is_running
        self._resume_btn.visible = is_paused
        self._cancel_btn.visible = is_running or is_paused
        self._start_without_task_btn.visible = is_idle or is_completed
        self._task_label.visible = bool(self._task_name) and not is_idle

        self.update()
