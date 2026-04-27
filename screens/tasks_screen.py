from __future__ import annotations

import flet as ft
from datetime import datetime

from api.tasks_api import (
    create_task,
    create_task_list,
    delete_task,
    delete_task_list,
    list_task_lists,
    list_tasks,
    update_task,
)
from state.app_state import app_state
from state.ws_client import register_handler, unregister_handler


# Priority color mapping
PRIORITY_COLORS = {
    "urgent": "#EF5350",    # Red
    "important": "#FFA726",  # Orange
    "normal": "#42A5F5",     # Blue
    "low": "#66BB6A",        # Green
}


class TasksScreen:
    """Tasks screen with lists sidebar and task list view."""

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.selected_list_id: str | None = None
        self.task_lists: list[dict] = []
        self.tasks: list[dict] = []

        # UI controls
        self.lists_column = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO)
        self.tasks_column = ft.Column(
            spacing=2, scroll=ft.ScrollMode.AUTO, expand=True)
        self.new_task_input = ft.TextField(label="Nueva tarea", expand=True)
        self.list_name_input = ft.TextField(label="Nombre de la lista")

        self.view = self._build_view()
        self._register_ws_handlers()
        self.page.run_task(self._load_data)

    def _register_ws_handlers(self) -> None:
        """Register WebSocket handlers for task updates."""
        async def on_task_list_updated(data: dict) -> None:
            await self._load_data()

        async def on_task_updated(data: dict) -> None:
            await self._load_data()

        register_handler("task_list.updated", on_task_list_updated)
        register_handler("task.updated", on_task_updated)

    def dispose(self) -> None:
        """Clean up WebSocket handlers."""
        unregister_handler("task_list.updated")
        unregister_handler("task.updated")

    def _build_view(self) -> ft.Control:
        """Build the main tasks view with sidebar and task area."""
        # Sidebar header
        sidebar_header = ft.Row(
            [ft.Text("Listas", weight=ft.FontWeight.BOLD, size=14)],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        # Add button for new list
        add_list_btn = ft.IconButton(
            icon=ft.Icons.ADD,
            tooltip="Nueva lista",
            on_click=self._show_new_list_dialog,
        )
        sidebar_header.controls.append(add_list_btn)

        # Main area header
        main_header = ft.Row(
            [ft.Text("Tareas", weight=ft.FontWeight.BOLD, size=14)],
            expand=True,
        )

        # Bottom bar for adding tasks
        add_task_row = ft.Row(
            [
                self.new_task_input,
                ft.IconButton(
                    icon=ft.Icons.ADD_CIRCLE,
                    on_click=self._add_task,
                ),
            ],
            spacing=5,
        )

        # Layout: sidebar on left, main area on right
        layout = ft.Row(
            [
                ft.Column(
                    [sidebar_header, self.lists_column],
                    width=200,
                ),
                ft.VerticalDivider(),
                ft.Column(
                    [main_header, self.tasks_column, add_task_row],
                    expand=True,
                ),
            ],
            expand=True,
        )

        return layout

    def _show_new_list_dialog(self, e: ft.ControlEvent) -> None:
        """Show dialog to create new task list."""
        def on_confirm(e: ft.ControlEvent) -> None:
            self.page.run_task(self._create_new_list)

            self.current_view: str = "lists"  # "lists" or "today"

        def on_cancel(e: ft.ControlEvent) -> None:
            self.page.close(dlg)

        dlg = ft.AlertDialog(
            title=ft.Text("Nueva lista de tareas"),
            content=ft.Container(
                self.list_name_input,
                padding=10,
            ),
            actions=[
                ft.TextButton("Crear", on_click=on_confirm),
                ft.TextButton("Cancelar", on_click=on_cancel),
            ],
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    async def _create_new_list(self) -> None:
        """Create a new task list."""
        name = self.list_name_input.value.strip()
        if not name:
            return

        await create_task_list(app_state.workspace_id, name)
        self.list_name_input.value = ""
        await self._load_data()
        self.page.update()

    async def _add_task(self, e: ft.ControlEvent) -> None:
        """Add a new task to the selected list."""
        if not self.selected_list_id:
            return

        title = self.new_task_input.value.strip()
        if not title:
            return

        await create_task(
            app_state.workspace_id,
            self.selected_list_id,
            title,
        )
        self.new_task_input.value = ""
        await self._load_data()
        self.page.update()

    async def _load_data(self) -> None:
        """Load task lists and tasks."""
        try:
            self.task_lists = await list_task_lists(app_state.workspace_id)
            await self._build_lists_sidebar()

            # Load tasks if a list is selected
            if self.selected_list_id:
                self.tasks = await list_tasks(
                    app_state.workspace_id,
                    list_id=self.selected_list_id,
                )
            else:
                self.tasks = await list_tasks(app_state.workspace_id)

            await self._build_tasks_list()
        except Exception:
            pass
        finally:
            self.page.update()

    async def _build_lists_sidebar(self) -> None:
        """Build sidebar with task lists."""
        self.lists_column.controls.clear()

        for task_list in self.task_lists:
            list_item = ft.Container(
                content=ft.Row(
                    [
                        ft.Text(task_list["name"], expand=True),
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE,
                            icon_size=16,
                            on_click=lambda e, lid=task_list["id"]: self.page.run_task(
                                self._delete_list, lid
                            ),
                        ),
                    ],
                    spacing=5,
                ),
                padding=8,
                bgcolor=task_list.get("color", "#F0F0F0"),
                border_radius=4,
                on_click=lambda e, lid=task_list["id"]: self.page.run_task(
                    self._select_list, lid
                ),
            )

            self.lists_column.controls.append(list_item)

    async def _build_tasks_list(self) -> None:
        """Build the tasks list in the main area."""
        self.tasks_column.controls.clear()

        if not self.tasks:
            self.tasks_column.controls.append(
                ft.Container(
                    ft.Text("No hay tareas", italic=True),
                    padding=20,
                ),
            )
            return

        for task in self.tasks:
            priority = task.get("priority", "normal")
            color = PRIORITY_COLORS.get(priority, "#42A5F5")
            status = task.get("status", "pending")

            # Task row
            task_row = ft.Container(
                content=ft.Row(
                    [
                        # Checkbox for toggling status
                        ft.Checkbox(
                            value=(status == "completed"),
                            on_change=lambda e, tid=task["id"]: self.page.run_task(
                                self._toggle_task_status, tid
                            ),
                        ),
                        # Title and details
                        ft.Column(
                            [
                                ft.Text(
                                    task["title"],
                                    size=13,
                                    weight=ft.FontWeight.W500,
                                ),
                                ft.Text(
                                    task.get("description", ""),
                                    size=11,
                                    color="gray",
                                ) if task.get("description") else ft.SizedBox(height=0),
                            ],
                            expand=True,
                            spacing=2,
                        ),
                        # Priority badge
                        ft.Container(
                            ft.Text(priority, size=9, color="white"),
                            padding=ft.Padding(4, 2, 4, 2),
                            bgcolor=color,
                            border_radius=3,
                        ),
                        # Due date
                        ft.Text(
                            task.get("due_date", ""),
                            size=10,
                            width=80,
                        ) if task.get("due_date") else ft.SizedBox(width=80),
                        # Delete button
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE,
                            icon_size=16,
                            on_click=lambda e, tid=task["id"]: self.page.run_task(
                                self._delete_task, tid
                            ),
                        ),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=8,
                border_radius=4,
                border=ft.border.all(1, "#E0E0E0"),
            )

            self.tasks_column.controls.append(task_row)

    async def _select_list(self, list_id: str) -> None:
        """Select a task list and load its tasks."""
        self.selected_list_id = list_id
        await self._load_data()

    async def _toggle_task_status(self, task_id: str) -> None:
        """Toggle task status between pending and completed."""
        task = next((t for t in self.tasks if t["id"] == task_id), None)
        if not task:
            return

        new_status = "completed" if task["status"] == "pending" else "pending"
        await update_task(
            app_state.workspace_id,
            task_id,
            status=new_status,
        )
        await self._load_data()

    async def _delete_task(self, task_id: str) -> None:
        """Delete a task."""
        await delete_task(app_state.workspace_id, task_id)
        await self._load_data()

    async def _delete_list(self, list_id: str) -> None:
        """Delete a task list."""
        await delete_task_list(app_state.workspace_id, list_id)
        if self.selected_list_id == list_id:
            self.selected_list_id = None
        await self._load_data()
