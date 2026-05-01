"""WebSocket client with timer tick/finished dispatch.

The timer.tick handler updates only the label text to avoid
redrawing the entire UI every second. The timer.finished handler
shows an on-screen notification and resets the display.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any

import flet as ft
import websockets

from config import BACKEND_URL

WS_URL = BACKEND_URL.replace("http://", "ws://").replace("https://", "wss://")

_ws_task: asyncio.Task[None] | None = None
_ws_active = False
_workspace_id: str | None = None
_handlers: dict[str, Callable[[dict[str, Any]], Awaitable[None] | None]] = {}

# References set by main.py so WS handlers can update the UI directly.
_timer_label: ft.Text | None = None
_timer_state_text: ft.Text | None = None
_timer_pause_btn: ft.Control | None = None
_timer_resume_btn: ft.Control | None = None
_timer_cancel_btn: ft.Control | None = None
_timer_start_btn: ft.Control | None = None
_timer_id: str | None = None
_page: ft.Page | None = None


def set_workspace_id(workspace_id: str | None) -> None:
    """Set the active workspace id used by the WebSocket client."""

    global _workspace_id
    _workspace_id = workspace_id


def register_handler(
    event_type: str,
    handler: Callable[[dict[str, Any]], Awaitable[None] | None],
) -> None:
    """Register a handler for a WebSocket event type."""

    _handlers[event_type] = handler


def unregister_handler(event_type: str) -> None:
    """Remove a handler for a WebSocket event type."""

    _handlers.pop(event_type, None)


# ── Timer display references (set by main.py) ────────────


def set_timer_refs(
    label: ft.Text,
    state_text: ft.Text,
    pause_btn: ft.Control,
    resume_btn: ft.Control,
    cancel_btn: ft.Control,
    start_btn: ft.Control,
    page: ft.Page,
) -> None:
    """Provide direct references to timer display controls.

    This allows the WS tick handler to update only the label text
    without touching the entire widget tree.
    """

    global _timer_label, _timer_state_text, _timer_pause_btn
    global _timer_resume_btn, _timer_cancel_btn, _timer_start_btn, _page
    _timer_label = label
    _timer_state_text = state_text
    _timer_pause_btn = pause_btn
    _timer_resume_btn = resume_btn
    _timer_cancel_btn = cancel_btn
    _timer_start_btn = start_btn
    _page = page


def set_active_timer_id(timer_id: str | None) -> None:
    """Set the currently active timer id for WS dispatching."""

    global _timer_id
    _timer_id = timer_id


# ── In-app notification ──────────────────────────────────


def _show_snackbar(message: str, color: str = ft.Colors.GREEN_400) -> None:
    """Show a brief snackbar notification on screen."""

    if _page is None:
        return
    _page.snack_bar = ft.SnackBar(
        content=ft.Text(message, color=ft.Colors.WHITE),
        bgcolor=color,
        duration=4000,
    )
    _page.snack_bar.open = True
    _page.update()


# ── Core tick / finished handlers ────────────────────────


async def _handle_timer_tick(data: Any) -> None:
    """Update only the label text on each tick.

    This avoids redrawing the entire UI every second.
    """

    if _timer_label is None:
        return

    remaining = 0
    if isinstance(data, list):
        if _timer_id:
            for tick in data:
                if tick.get("timer_id") == _timer_id:
                    remaining = tick.get("remaining_seconds", 0)
                    break
    elif isinstance(data, dict):
        remaining = data.get("remaining_seconds", 0)

    hours = remaining // 3600
    minutes = (remaining % 3600) // 60
    seconds = remaining % 60
    _timer_label.value = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    if remaining <= 60:
        _timer_label.color = ft.Colors.RED_400
        if _timer_state_text:
            _timer_state_text.value = "Finishing..."
    elif remaining <= 300:
        _timer_label.color = ft.Colors.ORANGE_400
        if _timer_state_text:
            _timer_state_text.value = ""
    else:
        _timer_label.color = ft.Colors.WHITE
        if _timer_state_text:
            _timer_state_text.value = ""

    # Only update the label, not the whole page
    _timer_label.update()
    if _timer_state_text:
        _timer_state_text.update()


async def _handle_timer_finished(data: Any) -> None:
    """Handle timer finished — show notification + reset display."""

    if _timer_label is None:
        return

    _timer_label.value = "00:00:00"
    _timer_label.color = ft.Colors.GREEN_400
    if _timer_state_text:
        _timer_state_text.value = "Completed"
        _timer_state_text.update()
    _timer_label.update()

    # Show on-screen notification
    task_name = data.get("task_name", "Timer") if isinstance(
        data, dict) else "Timer"
    _show_snackbar(f"{task_name} completed!", ft.Colors.GREEN_400)

    # Reset button visibility
    if _timer_pause_btn:
        _timer_pause_btn.visible = False
        _timer_pause_btn.update()
    if _timer_resume_btn:
        _timer_resume_btn.visible = False
        _timer_resume_btn.update()
    if _timer_cancel_btn:
        _timer_cancel_btn.visible = False
        _timer_cancel_btn.update()
    if _timer_start_btn:
        _timer_start_btn.visible = True
        _timer_start_btn.update()


# ── Message dispatch ─────────────────────────────────────


async def _dispatch_message(message: str) -> None:
    """Parse and dispatch one incoming WebSocket message."""

    try:
        payload = json.loads(message)
    except json.JSONDecodeError:
        return

    event_type = payload.get("type")
    data = payload.get("data", {})
    if not event_type:
        return

    # Built-in handlers run first, then registered handlers.
    if event_type == "timer.tick":
        await _handle_timer_tick(data)
    elif event_type == "timer.finished":
        await _handle_timer_finished(data)

    handler = _handlers.get(event_type)
    if handler is not None:
        result = handler(data)
        if asyncio.iscoroutine(result):
            await result


async def _run_connection() -> None:
    """Keep the WebSocket connection alive and reconnect if needed."""

    global _ws_active

    while _ws_active:
        if not _workspace_id:
            await asyncio.sleep(1)
            continue

        ws_path = f"{WS_URL}/ws/{_workspace_id}"
        try:
            async with websockets.connect(ws_path) as websocket:
                message = {
                    "type": "workspace.changed",
                    "data": {"workspace_id": _workspace_id},
                }
                await websocket.send(json.dumps(message))
                async for message in websocket:
                    await _dispatch_message(message)
        except Exception:
            await asyncio.sleep(2)


def start() -> None:
    """Start the background WebSocket client if it is not running."""

    global _ws_task, _ws_active
    if _ws_task is not None and not _ws_task.done():
        return

    _ws_active = True
    _ws_task = asyncio.create_task(_run_connection())


async def stop() -> None:
    """Stop the background WebSocket client."""

    global _ws_task, _ws_active
    _ws_active = False
    if _ws_task is not None:
        _ws_task.cancel()
        try:
            await _ws_task
        except asyncio.CancelledError:
            pass
        _ws_task = None
