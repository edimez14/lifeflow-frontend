from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Awaitable, Callable
from typing import Any

import websockets

BACKEND_URL = os.getenv("BACKEND_URL")
WS_URL = BACKEND_URL.replace("http://", "ws://").replace("https://", "wss://")

_ws_task: asyncio.Task[None] | None = None
_ws_active = False
_workspace_id: str | None = None
_handlers: dict[str, Callable[[dict[str, Any]], Awaitable[None] | None]] = {}


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

    handler = _handlers.get(event_type)
    if handler is None:
        return

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
                await websocket.send(json.dumps({"type": "workspace.changed", "data": {"workspace_id": _workspace_id}}))
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
