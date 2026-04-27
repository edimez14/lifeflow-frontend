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
    """Reusable task row for all task views."""

    def __init__(
        self,
        task: dict,
        on_toggle: Callable[[str, bool], None] | None = None,
        on_start_timer: Callable[[dict], None] | None = None,
        on_edit: Callable[[dict], None] | None = None,
        on_move: Callable[[dict], None] | None = None,
        on_delete: Callable[[str], None] | None = None,
    ) -> None:
        self.task = task
        self._on_toggle = on_toggle
        self._on_start_timer = on_start_timer
        self._on_edit = on_edit
        self._on_move = on_move
        self._on_delete = on_delete

        status = str(task.get("status", "pending"))
        is_completed = status == "completed"

        title_style = ft.TextStyle(
            decoration=ft.TextDecoration.LINE_THROUGH
            if is_completed
            else ft.TextDecoration.NONE,
            color=ft.Colors.GREY_600 if is_completed else ft.Colors.BLACK,
        )

        priority = str(task.get("priority", "normal"))
        priority_color = PRIORITY_COLORS.get(priority, "#42A5F5")

        due_date = str(task.get("due_date") or "")

        row = ft.Row(
            [
                ft.Checkbox(
                    value=is_completed,
                    on_change=self._handle_toggle,
                ),
                ft.Text(
                    str(task.get("title", "Untitled task")),
                    size=13,
                    expand=True,
                    style=title_style,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
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
                            text="Edit",
                            icon=ft.Icons.EDIT,
                            on_click=self._handle_edit,
                        ),
                        ft.PopupMenuItem(
                            text="Move",
                            icon=ft.Icons.DRIVE_FILE_MOVE,
                            on_click=self._handle_move,
                        ),
                        ft.PopupMenuItem(),
                        ft.PopupMenuItem(
                            text="Delete",
                            icon=ft.Icons.DELETE_OUTLINE,
                            on_click=self._handle_delete,
                        ),
                    ],
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        super().__init__(
            content=row,
            border=ft.border.all(1, ft.Colors.GREY_300),
            border_radius=6,
            padding=8,
            margin=ft.margin.only(bottom=6),
            bgcolor=ft.Colors.WHITE,
        )

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
