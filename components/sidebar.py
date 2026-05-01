from __future__ import annotations

from collections.abc import Callable

import flet as ft

from components.workspace_badge import WorkspaceBadge
from state.app_state import app_state


class Sidebar(ft.Container):
    """Primary navigation sidebar for Lifeflow."""

    def __init__(
        self,
        on_navigate: Callable[[str], None],
        on_back: Callable[[], None],
    ) -> None:
        workspace_name = str(app_state.user_data.get("workspace_name", ""))

        self._nav_calendar = ft.Button(
            content=ft.Text("Calendar / Calendario"),
            icon=ft.Icons.CALENDAR_MONTH,
            on_click=lambda e: on_navigate("calendar"),
        )
        self._nav_tasks = ft.Button(
            content=ft.Text("Tasks / Tareas"),
            icon=ft.Icons.CHECKLIST,
            on_click=lambda e: on_navigate("tasks"),
        )
        self._back_btn = ft.Button(
            content=ft.Text("Ver atras / Back"),
            icon=ft.Icons.ARROW_BACK,
            on_click=lambda e: on_back(),
        )

        badge = WorkspaceBadge(
            workspace_name=workspace_name,
            workspace_color="#6B7280",
        )

        super().__init__(
            width=220,
            padding=12,
            bgcolor=ft.Colors.GREY_50,
            border=ft.Border.all(1, ft.Colors.GREY_200),
            content=ft.Column(
                controls=[
                    badge,
                    ft.Divider(height=12, thickness=1),
                    self._nav_calendar,
                    self._nav_tasks,
                    ft.Container(expand=True),
                    self._back_btn,
                ],
                spacing=8,
                expand=True,
            ),
        )
