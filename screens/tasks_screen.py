from __future__ import annotations

from datetime import datetime

import flet as ft

from api.tasks_api import (
    create_subtask,
    create_task,
    create_task_list,
    delete_subtask,
    delete_task,
    delete_task_list,
    list_subtasks,
    list_task_lists,
    list_tasks,
    update_subtask,
    update_task,
)
from components.task_row import TaskRow
from state.app_state import app_state
from state.ws_client import register_handler, unregister_handler


class TasksScreen:
    """Tasks screen with list view, daily view and subtasks UI."""

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.current_view: str = "lists"
        self.selected_list_id: str | None = None
        self.task_lists: list[dict] = []
        self.tasks: list[dict] = []

        self.expanded_task_ids: set[str] = set()
        self.subtasks_by_task_id: dict[str, list[dict]] = {}
        self.task_row_controls: dict[str, TaskRow] = {}

        self.lists_column = ft.Column(
            spacing=4, scroll=ft.ScrollMode.AUTO, expand=True)
        self.tasks_column = ft.Column(
            spacing=2, scroll=ft.ScrollMode.AUTO, expand=True)
        self.new_task_input = ft.TextField(
            label="New task / Nueva tarea", expand=True)
        self.list_name_input = ft.TextField(
            label="List name / Nombre de lista")

        self.view = self._build_view()
        self._register_ws_handlers()
        self.page.run_task(self._load_data)

    def _register_ws_handlers(self) -> None:
        """Register handlers for task events."""

        async def on_task_list_updated(data: dict) -> None:
            await self._load_data()

        async def on_task_updated(data: dict) -> None:
            await self._handle_task_updated_event(data)

        register_handler("task_list.updated", on_task_list_updated)
        register_handler("task.updated", on_task_updated)

    def dispose(self) -> None:
        """Remove websocket handlers."""
        unregister_handler("task_list.updated")
        unregister_handler("task.updated")

    def _build_view(self) -> ft.Control:
        """Build main layout."""
        sidebar_header = ft.Row(
            controls=[
                ft.Text("Lists / Listas", weight=ft.FontWeight.BOLD, size=14),
                ft.IconButton(
                    icon=ft.Icons.ADD,
                    tooltip="Create list",
                    on_click=self._show_new_list_dialog,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        view_selector = ft.Row(
            controls=[
                ft.TextButton("Lists / Listas",
                              on_click=lambda e: self._switch_view("lists")),
                ft.TextButton(
                    "Today / Hoy", on_click=lambda e: self._switch_view("today")),
            ],
            spacing=6,
        )

        add_task_row = ft.Row(
            controls=[
                self.new_task_input,
                ft.IconButton(icon=ft.Icons.ADD_CIRCLE,
                              on_click=self._add_task),
            ],
            spacing=6,
        )

        return ft.Row(
            controls=[
                ft.Container(
                    width=240,
                    padding=10,
                    content=ft.Column(
                        controls=[sidebar_header, self.lists_column],
                        spacing=8,
                        expand=True,
                    ),
                ),
                ft.VerticalDivider(width=1),
                ft.Container(
                    expand=True,
                    padding=10,
                    content=ft.Column(
                        controls=[view_selector,
                                  self.tasks_column, add_task_row],
                        spacing=10,
                        expand=True,
                    ),
                ),
            ],
            expand=True,
        )

    def _switch_view(self, view: str) -> None:
        """Switch between list and today views."""
        self.current_view = view
        self.page.run_task(self._load_data)

    def _show_new_list_dialog(self, e: ft.ControlEvent) -> None:
        """Open dialog for list creation."""

        def on_confirm(_: ft.ControlEvent) -> None:
            self.page.run_task(self._create_new_list)
            dialog.open = False
            self.page.update()

        def on_cancel(_: ft.ControlEvent) -> None:
            dialog.open = False
            self.page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("New list / Nueva lista"),
            content=self.list_name_input,
            actions=[
                ft.TextButton("Create", on_click=on_confirm),
                ft.TextButton("Cancel", on_click=on_cancel),
            ],
        )

        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    async def _create_new_list(self) -> None:
        """Create a task list in current workspace."""
        if not app_state.workspace_id:
            return

        name = (self.list_name_input.value or "").strip()
        if not name:
            return

        await create_task_list(app_state.workspace_id, name)
        self.list_name_input.value = ""
        await self._load_data()

    async def _add_task(self, e: ft.ControlEvent) -> None:
        """Create a task in selected list."""
        if not app_state.workspace_id or not self.selected_list_id:
            return

        title = (self.new_task_input.value or "").strip()
        if not title:
            return

        await create_task(app_state.workspace_id, self.selected_list_id, title)
        self.new_task_input.value = ""
        await self._load_data()

    async def _load_data(self) -> None:
        """Load task lists and tasks."""
        if not app_state.workspace_id:
            return

        try:
            self.task_lists = await list_task_lists(app_state.workspace_id)

            if self.selected_list_id is None and self.task_lists:
                self.selected_list_id = str(self.task_lists[0]["id"])

            await self._build_lists_sidebar()

            if self.current_view == "today":
                await self._build_daily_view()
            else:
                await self._build_list_view()
        finally:
            self.page.update()

    async def _build_lists_sidebar(self) -> None:
        """Render all lists in sidebar."""
        self.lists_column.controls.clear()

        for task_list in self.task_lists:
            list_id = str(task_list["id"])
            is_selected = self.selected_list_id == list_id

            tile = ft.Container(
                padding=8,
                border_radius=6,
                bgcolor="#E8F0FE" if is_selected else task_list.get(
                    "color", "#F4F4F4"),
                content=ft.Row(
                    controls=[
                        ft.Text(str(task_list.get("name", "")), expand=True),
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE,
                            icon_size=16,
                            on_click=lambda e, lid=list_id: self.page.run_task(
                                self._delete_list, lid),
                        ),
                    ],
                    spacing=6,
                ),
                on_click=lambda e, lid=list_id: self.page.run_task(
                    self._select_list, lid),
            )
            self.lists_column.controls.append(tile)

    async def _build_list_view(self) -> None:
        """Render tasks for selected list."""
        self.tasks_column.controls.clear()
        self.task_row_controls.clear()

        if not app_state.workspace_id:
            return

        if self.selected_list_id:
            self.tasks = await list_tasks(app_state.workspace_id, list_id=self.selected_list_id)
        else:
            self.tasks = await list_tasks(app_state.workspace_id)

        await self._render_task_rows(self.tasks)

    async def _build_daily_view(self) -> None:
        """Render daily tasks grouped by list for today."""
        self.tasks_column.controls.clear()
        self.task_row_controls.clear()

        if not app_state.workspace_id:
            return

        all_tasks = await list_tasks(app_state.workspace_id)
        today_str = datetime.now().date().isoformat()

        tasks_today: dict[str, list[dict]] = {}
        for task in all_tasks:
            due_date = str(task.get("due_date") or "")
            if due_date != today_str:
                continue

            list_id = str(task.get("task_list_id") or "")
            tasks_today.setdefault(list_id, []).append(task)

        if not tasks_today:
            self.tasks_column.controls.append(
                ft.Container(
                    content=ft.Text(
                        "No tasks for today / No hay tareas para hoy", italic=True),
                    padding=16,
                )
            )
            return

        for task_list in self.task_lists:
            list_id = str(task_list["id"])
            items = tasks_today.get(list_id, [])
            if not items:
                continue

            self.tasks_column.controls.append(
                ft.Container(
                    content=ft.Text(
                        f"{task_list.get('name', 'List')} ({len(items)})",
                        weight=ft.FontWeight.BOLD,
                        size=13,
                    ),
                    padding=ft.padding.only(top=8, bottom=4),
                )
            )

            await self._render_task_rows(items)

        if self.selected_list_id:
            no_date_items = [
                task
                for task in all_tasks
                if str(task.get("task_list_id") or "") == self.selected_list_id
                and not task.get("due_date")
            ]
            if no_date_items:
                self.tasks_column.controls.append(
                    ft.Container(
                        content=ft.Text("No date / Sin fecha",
                                        weight=ft.FontWeight.BOLD, size=13),
                        padding=ft.padding.only(top=10, bottom=4),
                    )
                )
                await self._render_task_rows(no_date_items)

    async def _render_task_rows(self, items: list[dict]) -> None:
        """Render task rows, including expanded subtasks."""
        if not items:
            self.tasks_column.controls.append(
                ft.Container(
                    content=ft.Text("No tasks / No hay tareas", italic=True),
                    padding=16,
                )
            )
            return

        for task in items:
            task_id = str(task.get("id", ""))
            if task_id in self.expanded_task_ids:
                await self._load_subtasks_for_task(task_id)

            subtasks = self.subtasks_by_task_id.get(task_id, [])
            completion_percentage = self._calculate_completion_percentage(
                subtasks)

            self.tasks_column.controls.append(
                self._make_task_row(
                    task,
                    subtasks=subtasks,
                    is_expanded=task_id in self.expanded_task_ids,
                    completion_percentage=completion_percentage,
                )
            )
            self.task_row_controls[task_id] = self.tasks_column.controls[-1]

    async def _load_subtasks_for_task(self, task_id: str) -> None:
        """Load subtasks for one task and cache them."""
        if not app_state.workspace_id:
            return

        self.subtasks_by_task_id[task_id] = await list_subtasks(app_state.workspace_id, task_id)

    def _calculate_completion_percentage(self, subtasks: list[dict]) -> float:
        """Calculate completion percentage from subtasks."""
        if not subtasks:
            return 0.0

        completed = sum(1 for subtask in subtasks if bool(
            subtask.get("completed", False)))
        return (completed / len(subtasks)) * 100

    def _make_task_row(
        self,
        task: dict,
        subtasks: list[dict],
        is_expanded: bool,
        completion_percentage: float,
    ) -> TaskRow:
        """Create a TaskRow with actions wired to this screen."""
        return TaskRow(
            task=task,
            subtasks=subtasks,
            is_expanded=is_expanded,
            completion_percentage=completion_percentage,
            on_expand=self._handle_expand,
            on_toggle=self._handle_toggle,
            on_start_timer=self._handle_start_timer,
            on_edit=self._handle_edit,
            on_move=self._handle_move,
            on_delete=self._handle_delete,
            on_subtask_toggle=self._handle_subtask_toggle,
            on_subtask_add=self._handle_subtask_add,
            on_subtask_delete=self._handle_subtask_delete,
        )

    def _handle_expand(self, task_id: str) -> None:
        """Toggle expand state of one task row."""
        self.page.run_task(self._toggle_expand, task_id)

    async def _toggle_expand(self, task_id: str) -> None:
        """Async expand/collapse with lazy subtasks load."""
        if task_id in self.expanded_task_ids:
            self.expanded_task_ids.remove(task_id)
        else:
            self.expanded_task_ids.add(task_id)
            await self._load_subtasks_for_task(task_id)

        await self._load_data()

    def _handle_toggle(self, task_id: str, is_completed: bool) -> None:
        """Handle checkbox toggle from row component."""
        self.page.run_task(self._toggle_task_status, task_id, is_completed)

    def _handle_start_timer(self, task: dict) -> None:
        """Handle start timer action from row component."""
        self.page.snack_bar = ft.SnackBar(
            ft.Text("Timer module is coming soon"))
        self.page.snack_bar.open = True
        self.page.update()

    def _handle_edit(self, task: dict) -> None:
        """Handle edit action from row component."""
        self.page.snack_bar = ft.SnackBar(ft.Text("Edit task action"))
        self.page.snack_bar.open = True
        self.page.update()

    def _handle_move(self, task: dict) -> None:
        """Handle move action from row component."""
        self.page.snack_bar = ft.SnackBar(ft.Text("Move task action"))
        self.page.snack_bar.open = True
        self.page.update()

    def _handle_delete(self, task_id: str) -> None:
        """Handle delete action from row component."""
        self.page.run_task(self._delete_task, task_id)

    def _handle_subtask_toggle(self, task_id: str, subtask_id: str, is_completed: bool) -> None:
        """Handle subtask checkbox toggle from row component."""
        self.page.run_task(self._toggle_subtask_status,
                           task_id, subtask_id, is_completed)

    def _handle_subtask_add(self, task_id: str, title: str) -> None:
        """Handle inline subtask creation from row component."""
        self.page.run_task(self._create_inline_subtask, task_id, title)

    def _handle_subtask_delete(self, task_id: str, subtask_id: str) -> None:
        """Handle subtask delete from row component."""
        self.page.run_task(self._delete_inline_subtask, task_id, subtask_id)

    async def _select_list(self, list_id: str) -> None:
        """Select a list and reload."""
        self.selected_list_id = list_id
        await self._load_data()

    async def _toggle_task_status(self, task_id: str, is_completed: bool) -> None:
        """Update task status on API."""
        if not app_state.workspace_id:
            return

        status_value = "completed" if is_completed else "pending"
        await update_task(app_state.workspace_id, task_id, status=status_value)
        await self._load_data()

    async def _delete_task(self, task_id: str) -> None:
        """Delete task on API."""
        if not app_state.workspace_id:
            return

        await delete_task(app_state.workspace_id, task_id)
        self.expanded_task_ids.discard(task_id)
        self.subtasks_by_task_id.pop(task_id, None)
        await self._load_data()

    async def _delete_list(self, list_id: str) -> None:
        """Delete list on API."""
        if not app_state.workspace_id:
            return

        await delete_task_list(app_state.workspace_id, list_id)

        if self.selected_list_id == list_id:
            self.selected_list_id = None

        await self._load_data()

    async def _toggle_subtask_status(self, task_id: str, subtask_id: str, is_completed: bool) -> None:
        """Update subtask completion status."""
        if not app_state.workspace_id:
            return

        await update_subtask(
            app_state.workspace_id,
            task_id,
            subtask_id,
            completed=is_completed,
        )
        await self._load_subtasks_for_task(task_id)
        await self._load_data()

    async def _create_inline_subtask(self, task_id: str, title: str) -> None:
        """Create inline subtask for expanded task."""
        if not app_state.workspace_id:
            return

        current_subtasks = self.subtasks_by_task_id.get(task_id, [])
        next_order = len(current_subtasks)
        await create_subtask(
            app_state.workspace_id,
            task_id,
            title=title,
            completed=False,
            order=next_order,
        )
        await self._load_subtasks_for_task(task_id)
        await self._load_data()

    async def _delete_inline_subtask(self, task_id: str, subtask_id: str) -> None:
        """Delete one subtask from expanded task."""
        if not app_state.workspace_id:
            return

        await delete_subtask(app_state.workspace_id, task_id, subtask_id)
        await self._load_subtasks_for_task(task_id)
        await self._load_data()

    async def _handle_task_updated_event(self, data: dict) -> None:
        """Apply websocket task updates without reloading all rows."""
        if not isinstance(data, dict):
            return

        task_id = str(data.get("task_id") or data.get("id") or "")
        if not task_id:
            return

        if "subtask" in data:
            await self._apply_subtask_upsert(task_id, data["subtask"])
            await self._redraw_task_row(task_id)
            return

        if "subtask_id" in data:
            self._apply_subtask_delete(task_id, str(data.get("subtask_id") or ""))
            await self._redraw_task_row(task_id)
            return

        if self._is_task_payload(data):
            self._upsert_task_in_memory(data)
            await self._redraw_task_row(task_id)
            return

        self._remove_task_from_memory(task_id)
        self._remove_task_row_control(task_id)
        self.page.update()

    def _is_task_payload(self, data: dict) -> bool:
        """Detect if websocket payload contains full/partial task fields."""
        task_fields = {
            "title",
            "status",
            "priority",
            "due_date",
            "description",
            "task_list_id",
            "project_id",
            "order",
            "category_id",
        }
        return any(field in data for field in task_fields)

    def _upsert_task_in_memory(self, data: dict) -> None:
        """Update one task in local list memory."""
        task_id = str(data.get("id") or "")
        if not task_id:
            return

        for index, task in enumerate(self.tasks):
            if str(task.get("id")) == task_id:
                merged = {**task, **data}
                self.tasks[index] = merged
                return

        self.tasks.append(data)

    def _remove_task_from_memory(self, task_id: str) -> None:
        """Remove one task from local list memory."""
        self.tasks = [task for task in self.tasks if str(task.get("id")) != task_id]
        self.expanded_task_ids.discard(task_id)
        self.subtasks_by_task_id.pop(task_id, None)

    async def _apply_subtask_upsert(self, task_id: str, subtask: dict) -> None:
        """Insert or update one subtask in local cache."""
        if not isinstance(subtask, dict):
            return

        current = list(self.subtasks_by_task_id.get(task_id, []))
        subtask_id = str(subtask.get("id") or "")
        if not subtask_id:
            return

        updated = False
        for index, item in enumerate(current):
            if str(item.get("id")) == subtask_id:
                current[index] = {**item, **subtask}
                updated = True
                break

        if not updated:
            current.append(subtask)

        self.subtasks_by_task_id[task_id] = current

    def _apply_subtask_delete(self, task_id: str, subtask_id: str) -> None:
        """Delete one subtask from local cache."""
        current = self.subtasks_by_task_id.get(task_id, [])
        self.subtasks_by_task_id[task_id] = [
            item for item in current if str(item.get("id")) != subtask_id
        ]

    async def _redraw_task_row(self, task_id: str) -> None:
        """Redraw only one task row control in the current view."""
        old_row = self.task_row_controls.get(task_id)
        if old_row is None:
            return

        task = next((item for item in self.tasks if str(item.get("id")) == task_id), None)
        if task is None:
            self._remove_task_row_control(task_id)
            self.page.update()
            return

        subtasks = self.subtasks_by_task_id.get(task_id, [])
        completion_percentage = self._calculate_completion_percentage(subtasks)
        new_row = self._make_task_row(
            task,
            subtasks=subtasks,
            is_expanded=task_id in self.expanded_task_ids,
            completion_percentage=completion_percentage,
        )

        for index, control in enumerate(self.tasks_column.controls):
            if control is old_row:
                self.tasks_column.controls[index] = new_row
                self.task_row_controls[task_id] = new_row
                self.page.update()
                return

    def _remove_task_row_control(self, task_id: str) -> None:
        """Remove one row control from tasks column."""
        row = self.task_row_controls.pop(task_id, None)
        if row is None:
            return

        self.tasks_column.controls = [control for control in self.tasks_column.controls if control is not row]
