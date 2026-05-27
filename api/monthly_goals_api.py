from __future__ import annotations

from state.http_client import get, post, put, delete


async def fetch_monthly_goals_for_month(
    workspace_id: str, year: int, month: int
) -> list[dict]:
    """Return all monthly goals for a workspace, year, and month (supports multiple)."""
    response = await get(
        f"/workspaces/{workspace_id}/monthly-goals/{year}/{month}"
    )
    response.raise_for_status()
    return response.json()


async def create_monthly_goal(workspace_id: str, data: dict) -> dict:
    """Create a new monthly goal (always creates a new row)."""
    response = await post(
        f"/workspaces/{workspace_id}/monthly-goals/",
        json={
            "year": data["year"],
            "month": data["month"],
            "goal_text": data.get("goal_text", ""),
            "action_plan": data.get("action_plan", ""),
        },
    )
    response.raise_for_status()
    return response.json()


async def update_monthly_goal(
    workspace_id: str, goal_id: str, data: dict
) -> dict:
    """Update an existing monthly goal by its id."""
    response = await put(
        f"/workspaces/{workspace_id}/monthly-goals/{goal_id}",
        json={
            "goal_text": data.get("goal_text", ""),
            "action_plan": data.get("action_plan", ""),
            "is_completed": data.get("is_completed", False),
        },
    )
    response.raise_for_status()
    return response.json()


async def list_all_monthly_goals(workspace_id: str) -> list[dict]:
    """List all monthly goals for a workspace."""
    response = await get(f"/workspaces/{workspace_id}/monthly-goals/")
    response.raise_for_status()
    return response.json()


async def delete_monthly_goal(workspace_id: str, goal_id: str) -> None:
    """Delete a monthly goal by id."""
    response = await delete(
        f"/workspaces/{workspace_id}/monthly-goals/{goal_id}"
    )
    response.raise_for_status()
