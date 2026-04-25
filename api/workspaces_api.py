from __future__ import annotations

from state import http_client


async def list_workspaces() -> list[dict]:
    """Return all available workspaces."""

    response = await http_client.get("/workspaces")
    response.raise_for_status()
    return response.json()


async def auth_workspace(workspace_id: str, password: str | None = None) -> str:
    """Authenticate one workspace and return the access token."""

    payload = {"password": password}
    response = await http_client.post(f"/workspaces/{workspace_id}/auth", json=payload)
    response.raise_for_status()
    data = response.json()
    return str(data.get("access_token", ""))
