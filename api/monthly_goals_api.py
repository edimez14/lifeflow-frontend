from __future__ import annotations

from state.http_client import get_workspace_token, put, get, delete


async def fetch_monthly_goal(workspace_id: str, year: int, month: int) -> dict:
    """Return the monthly goal for a workspace and month, or empty fields."""
    response = await get(f"/workspaces/{workspace_id}/monthly-goals/{year}/{month}")
    response.raise_for_status()
    return response.json()


async def save_monthly_goal(workspace_id: str, year: int, month: int, data: dict) -> dict:
    """Create or update the monthly goal for a workspace and month."""
    # The PUT endpoint expects only goal_text and action_plan in the body
    payload = {
        "year": year,
        "month": month,
        "goal_text": data.get("goal_text", ""),
        "action_plan": data.get("action_plan", ""),
    }
    response = await put(
        f"/workspaces/{workspace_id}/monthly-goals/{year}/{month}",
        json=payload,
    )
    response.raise_for_status()
    return response.json()


async def list_all_monthly_goals(workspace_id: str) -> list[dict]:
    """List all monthly goals for a workspace."""
    response = await get(f"/workspaces/{workspace_id}/monthly-goals/")
    response.raise_for_status()
    return response.json()


async def delete_monthly_goal(workspace_id: str, year: int, month: int) -> None:
    """Delete a monthly goal by workspace, year and month."""
    response = await delete(
        f"/workspaces/{workspace_id}/monthly-goals/{year}/{month}"
    )
    response.raise_for_status()
