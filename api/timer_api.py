"""API client for timer endpoints."""

from __future__ import annotations

from state.http_client import get, post


async def start_timer(
    workspace_id: str,
    estimated_seconds: int = 0,
    task_id: str | None = None,
) -> dict:
    """Start a new timer session."""

    payload: dict = {
        "estimated_seconds": estimated_seconds,
    }
    if task_id is not None:
        payload["task_id"] = task_id

    response = await post(f"/workspaces/{workspace_id}/timers/start", json=payload)
    response.raise_for_status()
    return response.json()


async def pause_timer(timer_id: str, workspace_id: str) -> dict:
    """Pause a running timer."""

    response = await post(f"/workspaces/{workspace_id}/timers/{timer_id}/pause")
    response.raise_for_status()
    return response.json()


async def resume_timer(timer_id: str, workspace_id: str) -> dict:
    """Resume a paused timer."""

    response = await post(f"/workspaces/{workspace_id}/timers/{timer_id}/resume")
    response.raise_for_status()
    return response.json()


async def cancel_timer(timer_id: str, workspace_id: str) -> dict:
    """Cancel a running or paused timer."""

    response = await post(f"/workspaces/{workspace_id}/timers/{timer_id}/cancel")
    response.raise_for_status()
    return response.json()


async def get_timer(timer_id: str, workspace_id: str) -> dict:
    """Get details of one timer session."""

    response = await get(f"/workspaces/{workspace_id}/timers/{timer_id}")
    response.raise_for_status()
    return response.json()


async def get_timer_history(task_id: str, workspace_id: str) -> list[dict]:
    """Return timer session history for a task."""

    response = await get(f"/workspaces/{workspace_id}/timers/history/{task_id}")
    response.raise_for_status()
    return response.json()
