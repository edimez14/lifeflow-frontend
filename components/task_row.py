from __future__ import annotations

from collections.abc import Callable

import flet as ft


PRIORITY_COLORS = {
    "urgent": "#EF5350",
    "important": "#FFA726",
    "normal": "#42A5F5",
    "low": "#66BB6A",
}


class TaskRow(ft.Container):
    """Reusable task row with expandable subtasks."""

    def __init__(
        self,
        task: dict,
        subtasks: list[dict] | None = None,
        is_expanded: bool = False,
        completion_percentage: float = 0.0,
        on_expand: Callable[[str], None] | None = None,
        on_toggle: Callable[[str, bool], None] | None = None,
        on_start_timer: Callable[[dict], None] | None = None,
        on_edit: Callable[[dict], None] | None = None,
        on_move: Callable[[dict], None] | None = None,
        on_delete: Callable[[str], None] | None = None,
        on_subtask_toggle: Callable[[str, str, bool], None] | None = None,
        on_subtask_add: Callable[[str, str], None] | None = None,
        on_subtask_delete: Callable[[str, str], None] | None = None,
    ) -> None:
        self.task = task
        self.subtasks = subtasks or []
        self.is_expanded = is_expanded
        self.completion_percentage = completion_percentage
        self._on_expand = on_expand
        self._on_toggle = on_toggle
        self._on_start_timer = on_start_timer
        self._on_edit = on_edit
        self._on_move = on_move
        self._on_delete = on_delete
        self._on_subtask_toggle = on_subtask_toggle
        self._on_subtask_add = on_subtask_add
        self._on_subtask_delete = on_subtask_delete

        self._subtask_input = ft.TextField(
            hint_text="Add subtask / Añadir subtarea",
            dense=True,
            expand=True,
            height=36,
            text_size=12,
        )

        status = str(task.get("status", "pending"))
        is_completed = status == "completed"

        title_style = ft.TextStyle(
            decoration=ft.TextDecoration.LINE_THROUGH if is_completed else ft.TextDecoration.NONE,
            color=ft.Colors.GREY_600 if is_completed else ft.Colors.BLACK,
        )

        priority = str(task.get("priority", "normal"))
        priority_color = PRIORITY_COLORS.get(priority, "#42A5F5")
        due_date = str(task.get("due_date") or "")
        task_id = str(task.get("id", ""))

        expand_icon = ft.Icons.KEYBOARD_ARROW_DOWN if is_expanded else ft.Icons.KEYBOARD_ARROW_RIGHT

        main_row = ft.Row(
            [
                ft.IconButton(
                    icon=expand_icon,
                    icon_size=18,
                    tooltip="Expand subtasks",
                    on_click=self._handle_expand,
                ),
                ft.Checkbox(value=is_completed, on_change=self._handle_toggle),
                ft.TextButton(
                    text=str(task.get("title", "Untitled task")),
                    style=ft.ButtonStyle(padding=ft.padding.all(0)),
                    on_click=self._handle_expand,
                ),
                ft.Container(
                    content=ft.Text(f"{completion_percentage:.0f}%",
                                    size=10, color=ft.Colors.GREY_700),
                    width=40,
                    alignment=ft.alignment.center_right,
                ),
                ft.Container(
                    content=ft.Text(priority, size=10, color=ft.Colors.WHITE),
                    bgcolor=priority_color,
                    border_radius=4,
                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                ),
                ft.Container(
                    content=ft.Text(due_date if due_date else "-", size=11),
                    width=95,
                    alignment=ft.alignment.center_right,
                ),
                ft.IconButton(
                    icon=ft.Icons.TIMER,
                    tooltip="Start timer",
                    icon_size=18,
                    on_click=self._handle_start_timer,
                ),
                ft.PopupMenuButton(
                    icon=ft.Icons.MORE_VERT,
                    tooltip="Task options",
                    items=[
                        ft.PopupMenuItem(
                            text="Edit", icon=ft.Icons.EDIT, on_click=self._handle_edit),
                        ft.PopupMenuItem(
                            text="Move", icon=ft.Icons.DRIVE_FILE_MOVE, on_click=self._handle_move),
                        ft.PopupMenuItem(),
                        ft.PopupMenuItem(
                            text="Delete", icon=ft.Icons.DELETE_OUTLINE, on_click=self._handle_delete),
                    ],
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        content_controls: list[ft.Control] = [main_row]

        if is_expanded:
            subtasks_column = ft.Column(spacing=4)

            for subtask in self.subtasks:
                subtask_id = str(subtask.get("id", ""))
                subtask_completed = bool(subtask.get("completed", False))
                subtask_title_style = ft.TextStyle(
                    decoration=ft.TextDecoration.LINE_THROUGH if subtask_completed else ft.TextDecoration.NONE,
                    color=ft.Colors.GREY_600 if subtask_completed else ft.Colors.BLACK,
                )

                subtasks_column.controls.append(
                    ft.Container(
                        padding=ft.padding.only(left=44, right=4),
                        content=ft.Row(
                            [
                                ft.Checkbox(
                                    value=subtask_completed,
                                    scale=0.9,
                                    on_change=lambda e, tid=task_id, sid=subtask_id: self._handle_subtask_toggle(
                                        e, tid, sid),
                                ),
                                ft.Text(
                                    str(subtask.get("title", "Subtask")),
                                    size=12,
                                    style=subtask_title_style,
                                    expand=True,
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.CLOSE,
                                    icon_size=14,
                                    tooltip="Delete subtask",
                                    on_click=lambda e, tid=task_id, sid=subtask_id: self._handle_subtask_delete(
                                        tid, sid),
                                ),
                            ],
                            spacing=6,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    )
                )

            subtasks_column.controls.append(
                ft.Container(
                    padding=ft.padding.only(left=44, right=4, top=2, bottom=2),
                    content=ft.Row(
                        [
                            self._subtask_input,
                            ft.IconButton(
                                icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                                icon_size=18,
                                tooltip="Add subtask",
                                on_click=self._handle_subtask_add,
                            ),
                        ],
                        spacing=6,
                    ),
                )
            )

            content_controls.append(subtasks_column)

        super().__init__(
            content=ft.Column(content_controls, spacing=4),
            border=ft.border.all(1, ft.Colors.GREY_300),
            border_radius=6,
            padding=8,
            margin=ft.margin.only(bottom=6),
            bgcolor=ft.Colors.WHITE,
        )

    def _handle_expand(self, e: ft.ControlEvent) -> None:
        if self._on_expand:
            self._on_expand(str(self.task.get("id", "")))

    def _handle_toggle(self, e: ft.ControlEvent) -> None:
        if self._on_toggle:
            self._on_toggle(str(self.task.get("id", "")),
                            bool(e.control.value))

    def _handle_start_timer(self, e: ft.ControlEvent) -> None:
        if self._on_start_timer:
            self._on_start_timer(self.task)

    def _handle_edit(self, e: ft.ControlEvent) -> None:
        if self._on_edit:
            self._on_edit(self.task)

    def _handle_move(self, e: ft.ControlEvent) -> None:
        if self._on_move:
            self._on_move(self.task)

    def _handle_delete(self, e: ft.ControlEvent) -> None:
        if self._on_delete:
            self._on_delete(str(self.task.get("id", "")))

    def _handle_subtask_toggle(self, e: ft.ControlEvent, task_id: str, subtask_id: str) -> None:
        if self._on_subtask_toggle:
            self._on_subtask_toggle(task_id, subtask_id, bool(e.control.value))

    def _handle_subtask_add(self, e: ft.ControlEvent) -> None:
        if not self._on_subtask_add:
            return

        title = (self._subtask_input.value or "").strip()
        if not title:
            return

        self._on_subtask_add(str(self.task.get("id", "")), title)
        self._subtask_input.value = ""

    def _handle_subtask_delete(self, task_id: str, subtask_id: str) -> None:
        if self._on_subtask_delete:
            self._on_subtask_delete(task_id, subtask_id)
