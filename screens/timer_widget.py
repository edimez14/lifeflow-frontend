"""Persistent timer widget shown as a side panel."""

from __future__ import annotations

import asyncio
from typing import Any

import flet as ft

from api.timer_api import cancel_timer, pause_timer, resume_timer, start_timer
from components.timer_display import TimerDisplay
from state.app_state import app_state
from state.ws_client import register_handler, unregister_handler


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
        self._pause_btn = ft.ElevatedButton(
            "Pause",
            icon=ft.Icons.PAUSE_CIRCLE_FILLED,
            visible=False,
            on_click=self._on_pause,
        )
        self._resume_btn = ft.ElevatedButton(
            "Resume",
            icon=ft.Icons.PLAY_CIRCLE_FILLED,
            visible=False,
            on_click=self._on_resume,
        )
        self._cancel_btn = ft.ElevatedButton(
            "Cancel",
            icon=ft.Icons.STOP_CIRCLE,
            visible=False,
            on_click=self._on_cancel,
        )
        self._start_without_task_btn = ft.ElevatedButton(
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

        self._register_ws_handlers()

    def _register_ws_handlers(self) -> None:
        """Register WebSocket event handlers for timer updates."""

        register_handler("timer.tick", self._on_tick)
        register_handler("timer.finished", self._on_finished)
        register_handler("timer.started", self._on_started)
        register_handler("timer.paused", self._on_paused)
        register_handler("timer.resumed", self._on_resumed)
        register_handler("timer.cancelled", self._on_cancelled)

    def dispose(self) -> None:
        """Unregister WS handlers when the widget is discarded."""

        unregister_handler("timer.tick")
        unregister_handler("timer.finished")
        unregister_handler("timer.started")
        unregister_handler("timer.paused")
        unregister_handler("timer.resumed")
        unregister_handler("timer.cancelled")

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
        except Exception:
            pass

    async def _on_resume(self, _: ft.ControlEvent) -> None:
        """Resume the paused timer."""

        if not self._timer_id or not app_state.workspace_id:
            return

        try:
            await resume_timer(self._timer_id, app_state.workspace_id)
        except Exception:
            pass

    async def _on_cancel(self, _: ft.ControlEvent) -> None:
        """Cancel the active timer."""

        if not self._timer_id or not app_state.workspace_id:
            return

        try:
            await cancel_timer(self._timer_id, app_state.workspace_id)
        except Exception:
            pass

    # ── WS handlers ──────────────────────────────────────

    async def _on_tick(self, data: Any) -> None:
        """Update the display on each tick."""

        if isinstance(data, list):
            for tick in data:
                timer_id = tick.get("timer_id")
                if timer_id == self._timer_id:
                    remaining = tick.get("remaining_seconds", 0)
                    is_paused = self._status == "paused"
                    self._display.update_display(remaining, is_paused)
                    break
        elif isinstance(data, dict):
            timer_id = data.get("timer_id")
            if timer_id == self._timer_id:
                remaining = data.get("remaining_seconds", 0)
                is_paused = self._status == "paused"
                self._display.update_display(remaining, is_paused)

    async def _on_finished(self, data: Any) -> None:
        """Handle timer finished event."""

        timer_id = data.get("timer_id") if isinstance(data, dict) else None
        if timer_id and timer_id == self._timer_id:
            self._status = "completed"
            self._display.show_completed()
            self._update_ui_state()

    async def _on_started(self, data: Any) -> None:
        """Handle timer started event."""

        if isinstance(data, dict):
            self._timer_id = data.get("id")
            self._task_id = data.get("task_id")
            self._status = "running"
            self._display.update_display(data.get("estimated_seconds", 0))
            self._update_task_display()
            self._update_ui_state()

    async def _on_paused(self, data: Any) -> None:
        """Handle timer paused event."""

        if isinstance(data, dict) and data.get("id") == self._timer_id:
            self._status = "paused"
            self._display.update_display(0, is_paused=True)
            self._update_ui_state()

    async def _on_resumed(self, data: Any) -> None:
        """Handle timer resumed event."""

        if isinstance(data, dict) and data.get("id") == self._timer_id:
            self._status = "running"
            self._display.update_display(0)
            self._update_ui_state()

    async def _on_cancelled(self, data: Any) -> None:
        """Handle timer cancelled event."""

        if isinstance(data, dict) and data.get("id") == self._timer_id:
            self._status = "idle"
            self._timer_id = None
            self._display.show_idle()
            self._update_ui_state()

    def reset(self) -> None:
        """Reset the widget to idle state."""

        self._timer_id = None
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
