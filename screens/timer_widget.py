"""Persistent timer widget with countdown, presets, and editable input."""

from __future__ import annotations

import asyncio
import json

import flet as ft

from api.timer_api import cancel_timer, pause_timer, resume_timer, start_timer
from components.timer_display import TimerDisplay
from state import ws_client
from state.app_state import app_state

SESSION_KEY = "timer_presets"


class TimerWidget(ft.Container):
    """Side panel widget with countdown timer and saved presets."""

    def __init__(self) -> None:
        self._timer_id: str | None = None
        self._task_id: str | None = None
        self._status: str = "idle"
        self._task_name: str = ""
        self._countdown_task: asyncio.Task[None] | None = None
        self._remaining_seconds: int = 0
        self._presets: list[dict] = []

        self._display = TimerDisplay()
        self._task_label = ft.Text(
            "",
            size=13,
            weight=ft.FontWeight.W_600,
            color=ft.Colors.WHITE,
            text_align=ft.TextAlign.CENTER,
            overflow=ft.TextOverflow.ELLIPSIS,
        )

        # ── Control buttons ─────────────────────────────────
        self._play_btn = ft.FilledButton(
            "Start",
            icon=ft.Icons.PLAY_ARROW,
            on_click=self._on_play,
        )
        self._pause_btn = ft.FilledButton(
            "Pause",
            icon=ft.Icons.PAUSE,
            visible=False,
            on_click=self._on_pause,
        )
        self._resume_btn = ft.FilledButton(
            "Resume",
            icon=ft.Icons.PLAY_ARROW,
            visible=False,
            on_click=self._on_resume,
        )
        self._cancel_btn = ft.OutlinedButton(
            "Cancel",
            icon=ft.Icons.CLOSE,
            visible=False,
            on_click=self._on_cancel,
        )

        control_row = ft.Row(
            controls=[self._play_btn, self._pause_btn,
                      self._resume_btn, self._cancel_btn],
            spacing=6,
            alignment=ft.MainAxisAlignment.CENTER,
        )

        # ── Presets section ─────────────────────────────────
        self._presets_title = ft.Text(
            "Saved times",
            size=12,
            weight=ft.FontWeight.W_700,
            color=ft.Colors.GREY_300,
        )
        self._save_preset_btn = ft.TextButton(
            "Save current",
            icon=ft.Icons.BOOKMARK_ADD_OUTLINED,
            on_click=self._on_save_preset,
        )
        self._presets_list = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO)
        presets_section = ft.Column(
            controls=[
                ft.Divider(height=1, color=ft.Colors.GREY_700),
                ft.Row(
                    [self._presets_title, self._save_preset_btn],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                self._presets_list,
            ],
            spacing=6,
            visible=False,
        )
        self._presets_section = presets_section

        super().__init__(
            bgcolor=ft.Colors.GREY_800,
            border_radius=12,
            padding=16,
            width=220,
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
                    ft.Container(height=4),
                    self._display,
                    ft.Container(height=4),
                    control_row,
                    ft.Container(height=4),
                    presets_section,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
            ),
        )

    # ── Public API (called from tasks_screen, ws_client) ────

    def set_task_info(self, task_name: str, task_id: str | None = None) -> None:
        """Set the active task name shown in the widget."""
        self._task_name = task_name
        self._task_id = task_id
        self._update_task_display()

    def _update_task_display(self) -> None:
        if self._task_name and self._status != "idle":
            self._task_label.value = self._task_name
            self._task_label.visible = True
        else:
            self._task_label.visible = False
        self.update()

    def reset(self) -> None:
        """Reset the widget to idle state."""
        self._stop_countdown()
        self._timer_id = None
        ws_client.set_active_timer_id(None)
        self._task_id = None
        self._status = "idle"
        self._task_name = ""
        self._display.show_idle()
        self._update_ui_state()

    # ── Error helper ────────────────────────────────────────

    def _show_error(self, message: str) -> None:
        if not self.page:
            return
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(message, color=ft.Colors.WHITE),
            bgcolor=ft.Colors.RED_400,
        )
        self.page.snack_bar.open = True
        self.page.update()

    # ── Countdown logic (local) ─────────────────────────────

    async def _countdown_loop(self, total_seconds: int) -> None:
        """Local countdown loop, ticks every second."""
        self._remaining_seconds = total_seconds
        while self._remaining_seconds > 0:
            if self._status == "paused":
                await asyncio.sleep(0.2)
                continue
            self._display.update_display(self._remaining_seconds)
            await asyncio.sleep(1)
            self._remaining_seconds -= 1

        # Finished
        if self._status in ("running", "paused"):
            self._status = "completed"
            self._display.show_completed()
            self._update_ui_state()
            if self.page:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text("Timer completed!",
                                    color=ft.Colors.WHITE),
                    bgcolor=ft.Colors.GREEN_400,
                    duration=4000,
                )
                self.page.snack_bar.open = True
                self.page.update()

    def _start_countdown(self, seconds: int) -> None:
        """Start (or restart) the countdown with given seconds."""
        self._stop_countdown()
        self._remaining_seconds = seconds
        self._countdown_task = asyncio.create_task(
            self._countdown_loop(seconds))

    def _stop_countdown(self) -> None:
        """Cancel the countdown loop if running."""
        if self._countdown_task is not None and not self._countdown_task.done():
            self._countdown_task.cancel()
        self._countdown_task = None

    # ── Button handlers ─────────────────────────────────────

    async def _on_play(self, _: ft.ControlEvent) -> None:
        """Validate input and start countdown (and backend timer)."""
        valid, msg = self._display.validate_input()
        if not valid:
            self._show_error(msg)
            return

        seconds = self._display.get_input_seconds()

        # Start backend timer for tracking (if workspace is set)
        if app_state.workspace_id:
            try:
                result = await start_timer(
                    workspace_id=app_state.workspace_id,
                    estimated_seconds=seconds,
                )
                self._timer_id = result["id"]
                ws_client.set_active_timer_id(self._timer_id)
            except Exception:
                # Non-blocking: countdown still works locally
                pass

        self._status = "running"
        self._display.update_display(seconds)
        self._start_countdown(seconds)
        self._update_ui_state()

    async def _on_pause(self, _: ft.ControlEvent) -> None:
        """Pause the countdown."""
        self._status = "paused"

        if self._timer_id and app_state.workspace_id:
            try:
                await pause_timer(self._timer_id, app_state.workspace_id)
            except Exception:
                pass

        self._display.update_display(self._remaining_seconds, is_paused=True)
        self._update_ui_state()

    async def _on_resume(self, _: ft.ControlEvent) -> None:
        """Resume the countdown."""
        self._status = "running"

        if self._timer_id and app_state.workspace_id:
            try:
                await resume_timer(self._timer_id, app_state.workspace_id)
            except Exception:
                pass

        self._display.update_display(self._remaining_seconds)
        self._update_ui_state()

    async def _on_cancel(self, _: ft.ControlEvent) -> None:
        """Cancel timer and return to idle."""
        self._stop_countdown()

        if self._timer_id and app_state.workspace_id:
            try:
                await cancel_timer(self._timer_id, app_state.workspace_id)
            except Exception:
                pass

        ws_client.set_active_timer_id(None)
        self._timer_id = None
        self._status = "idle"
        self._display.show_idle()
        self._update_ui_state()

    # ── Presets ─────────────────────────────────────────────

    def _load_presets(self) -> None:
        """Load presets from session."""
        if not self.page:
            return
        try:
            raw = self.page.session.get(SESSION_KEY)
        except Exception:
            raw = None
        if raw:
            try:
                self._presets = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                self._presets = []
        else:
            # Default presets
            self._presets = [
                {"name": "Pomodoro", "seconds": 1500},
                {"name": "Short break", "seconds": 300},
                {"name": "Long break", "seconds": 600},
            ]
            self._save_presets()
        self._render_presets()

    def _save_presets(self) -> None:
        """Save presets to session."""
        if not self.page:
            return
        try:
            self.page.session.set(
                SESSION_KEY, json.dumps(self._presets))
        except Exception:
            pass

    def _render_presets(self) -> None:
        """Rebuild the presets list UI."""
        self._presets_list.controls.clear()
        if not self._presets:
            self._presets_section.visible = False
            self.update()
            return

        self._presets_section.visible = True

        for idx, preset in enumerate(self._presets):
            name = preset.get("name", "Unnamed")
            seconds = preset.get("seconds", 0)
            label = f"{name} ({self._format_duration(seconds)})"

            row = ft.Row(
                controls=[
                    ft.Text(label, size=11, color=ft.Colors.WHITE,
                            expand=True, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.IconButton(
                        icon=ft.Icons.PLAY_ARROW,
                        icon_size=16,
                        icon_color=ft.Colors.GREEN_400,
                        tooltip="Load",
                        on_click=lambda e, s=seconds: self._load_preset(s),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_size=14,
                        icon_color=ft.Colors.RED_400,
                        tooltip="Delete",
                        on_click=lambda e, i=idx: self._delete_preset(i),
                    ),
                ],
                spacing=2,
                alignment=ft.MainAxisAlignment.START,
            )
            self._presets_list.controls.append(row)

        self.update()

    def _format_duration(self, seconds: int) -> str:
        """Format seconds to MM:SS or HH:MM:SS."""
        if seconds >= 3600:
            h = seconds // 3600
            m = (seconds % 3600) // 60
            s = seconds % 60
            return f"{h:02d}:{m:02d}:{s:02d}"
        m = seconds // 60
        s = seconds % 60
        return f"{m:02d}:{s:02d}"

    def _load_preset(self, seconds: int) -> None:
        """Load a preset into the input field."""
        self._display.set_input_from_seconds(seconds)
        if self.page:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Loaded {self._format_duration(seconds)}",
                                color=ft.Colors.WHITE),
                bgcolor=ft.Colors.GREY_700,
                duration=1500,
            )
            self.page.snack_bar.open = True
            self.page.update()

    def _delete_preset(self, index: int) -> None:
        """Delete a preset by index."""
        if 0 <= index < len(self._presets):
            self._presets.pop(index)
            self._save_presets()
            self._render_presets()

    async def _on_save_preset(self, _: ft.ControlEvent) -> None:
        """Show a dialog to save the current time as a preset."""
        if not self.page:
            return

        seconds = self._display.get_input_seconds()
        if seconds < 1:
            self._show_error("Set a time first")
            return

        name_field = ft.TextField(
            label="Preset name",
            value=f"Custom {self._format_duration(seconds)}",
            autofocus=True,
        )

        async def _do_save(_: ft.ControlEvent) -> None:
            name = (name_field.value or "").strip()
            if not name:
                name = self._format_duration(seconds)
            self._presets.append({"name": name, "seconds": seconds})
            self._save_presets()
            self._render_presets()
            dlg.open = False
            self.page.update()
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Saved '{name}'", color=ft.Colors.WHITE),
                bgcolor=ft.Colors.GREEN_400,
                duration=2000,
            )
            self.page.snack_bar.open = True
            self.page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Save time"),
            content=ft.Column([name_field], tight=True, width=240),
            actions=[
                ft.TextButton(
                    "Cancel", on_click=lambda e: self.page.close(dlg)),
                ft.Button("Save", on_click=_do_save),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        dlg.open = True
        self.page.overlay.append(dlg)
        self.page.update()

    # ── UI state management ─────────────────────────────────

    def _update_ui_state(self) -> None:
        """Show/hide buttons based on timer status."""
        is_running = self._status == "running"
        is_paused = self._status == "paused"
        is_idle = self._status == "idle"
        is_completed = self._status == "completed"

        self._play_btn.visible = is_idle or is_completed
        self._pause_btn.visible = is_running
        self._resume_btn.visible = is_paused
        self._cancel_btn.visible = is_running or is_paused

        self._task_label.visible = bool(self._task_name) and not is_idle

        # Lazy-load presets once page is available
        if not self._presets and self.page is not None:
            self._load_presets()

        self.update()
