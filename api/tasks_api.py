from __future__ import annotations

from state import http_client


# ---------- TaskLists ----------


async def list_task_lists(workspace_id: str) -> list[dict]:
    """Get all task lists for a workspace."""
    response = await http_client.get(f"/workspaces/{workspace_id}/task-lists")
    response.raise_for_status()
    return response.json()


async def create_task_list(workspace_id: str, name: str, color: str | None = None) -> dict:
    """Create a new task list."""
    payload = {"name": name}
    if color:
        payload["color"] = color
    response = await http_client.post(f"/workspaces/{workspace_id}/task-lists", json=payload)
    response.raise_for_status()
    return response.json()


async def update_task_list(workspace_id: str, task_list_id: str, name: str | None = None, color: str | None = None) -> dict:
    """Update a task list."""
    payload = {}
    if name is not None:
        payload["name"] = name
    if color is not None:
        payload["color"] = color
    response = await http_client.put(f"/workspaces/{workspace_id}/task-lists/{task_list_id}", json=payload)
    response.raise_for_status()
    return response.json()


async def delete_task_list(workspace_id: str, task_list_id: str) -> None:
    """Delete a task list."""
    response = await http_client.delete(f"/workspaces/{workspace_id}/task-lists/{task_list_id}")
    response.raise_for_status()


# ---------- Tasks ----------


async def list_tasks(
    workspace_id: str,
    list_id: str | None = None,
    status_filter: str | None = None,
    priority: str | None = None,
    due_date: str | None = None,
) -> list[dict]:
    """Get tasks for a workspace with optional filters."""
    params = {}
    if list_id:
        params["list_id"] = list_id
    if status_filter:
        params["status"] = status_filter
    if priority:
        params["priority"] = priority
    if due_date:
        params["due_date"] = due_date

    response = await http_client.get(f"/workspaces/{workspace_id}/tasks", params=params)
    response.raise_for_status()
    return response.json()


async def create_task(
    workspace_id: str,
    task_list_id: str,
    title: str,
    description: str | None = None,
    priority: str | None = None,
    due_date: str | None = None,
) -> dict:
    """Create a new task."""
    payload = {"task_list_id": task_list_id, "title": title}
    if description:
        payload["description"] = description
    if priority:
        payload["priority"] = priority
    if due_date:
        payload["due_date"] = due_date

    response = await http_client.post(f"/workspaces/{workspace_id}/tasks", json=payload)
    response.raise_for_status()
    return response.json()


async def update_task(
    workspace_id: str,
    task_id: str,
    title: str | None = None,
    description: str | None = None,
    priority: str | None = None,
    due_date: str | None = None,
    status: str | None = None,
) -> dict:
    """Update a task."""
    payload = {}
    if title is not None:
        payload["title"] = title
    if description is not None:
        payload["description"] = description
    if priority is not None:
        payload["priority"] = priority
    if due_date is not None:
        payload["due_date"] = due_date
    if status is not None:
        payload["status"] = status

    response = await http_client.put(f"/workspaces/{workspace_id}/tasks/{task_id}", json=payload)
    response.raise_for_status()
    return response.json()


async def delete_task(workspace_id: str, task_id: str) -> None:
    """Delete a task."""
    response = await http_client.delete(f"/workspaces/{workspace_id}/tasks/{task_id}")
    response.raise_for_status()


async def reorder_tasks(workspace_id: str, reorders: list[dict]) -> None:
    """Reorder multiple tasks."""
    payload = {"reorders": reorders}
    response = await http_client.post(f"/workspaces/{workspace_id}/tasks/reorder", json=payload)
    response.raise_for_status()


# ---------- SubTasks ----------


async def list_subtasks(workspace_id: str, task_id: str) -> list[dict]:
    """Get all subtasks for one task."""
    response = await http_client.get(f"/workspaces/{workspace_id}/tasks/{task_id}/subtasks")
    response.raise_for_status()
    return response.json()


async def create_subtask(
    workspace_id: str,
    task_id: str,
    title: str,
    completed: bool = False,
    order: int = 0,
) -> dict:
    """Create a subtask for one task."""
    payload = {
        "title": title,
        "completed": completed,
        "order": order,
    }
    response = await http_client.post(f"/workspaces/{workspace_id}/tasks/{task_id}/subtasks", json=payload)
    response.raise_for_status()
    return response.json()


async def update_subtask(
    workspace_id: str,
    task_id: str,
    subtask_id: str,
    title: str | None = None,
    completed: bool | None = None,
    order: int | None = None,
) -> dict:
    """Update one subtask."""
    payload = {}
    if title is not None:
        payload["title"] = title
    if completed is not None:
        payload["completed"] = completed
    if order is not None:
        payload["order"] = order

    response = await http_client.put(
        f"/workspaces/{workspace_id}/tasks/{task_id}/subtasks/{subtask_id}",
        json=payload,
    )
    response.raise_for_status()
    return response.json()


async def delete_subtask(workspace_id: str, task_id: str, subtask_id: str) -> None:
    """Delete one subtask."""
    response = await http_client.delete(f"/workspaces/{workspace_id}/tasks/{task_id}/subtasks/{subtask_id}")
    response.raise_for_status()
