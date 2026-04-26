from __future__ import annotations

from datetime import datetime

from state.http_client import get, post, put, delete


async def fetch_calendars(workspace_id: str) -> list[dict]:
    """Return all calendars for a workspace."""
    response = await get(f"/workspaces/{workspace_id}/calendars")
    response.raise_for_status()
    return response.json()


async def fetch_events(workspace_id: str, start: datetime, end: datetime) -> list[dict]:
    """Return events in a date range for a workspace."""
    params = {
        "start": start.isoformat(),
        "end": end.isoformat(),
    }
    response = await get(f"/workspaces/{workspace_id}/events", params=params)
    response.raise_for_status()
    return response.json()


async def create_event(workspace_id: str, data: dict) -> dict:
    """Create a new event inside a workspace."""
    response = await post(f"/workspaces/{workspace_id}/events", json=data)
    response.raise_for_status()
    return response.json()


async def update_event(workspace_id: str, event_id: str, data: dict) -> dict:
    """Update an existing event."""
    response = await put(f"/workspaces/{workspace_id}/events/{event_id}", json=data)
    response.raise_for_status()
    return response.json()


async def delete_event(workspace_id: str, event_id: str) -> None:
    """Delete an event."""
    response = await delete(f"/workspaces/{workspace_id}/events/{event_id}")
    response.raise_for_status()
