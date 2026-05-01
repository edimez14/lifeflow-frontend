from __future__ import annotations

from collections.abc import Callable

import flet as ft


class WorkspaceBadge(ft.Container):
    """Small badge that shows the active workspace name and color."""

    def __init__(
        self,
        workspace_name: str,
        workspace_color: str,
        on_click: Callable[[ft.ControlEvent], None] | None = None,
    ) -> None:
        label = workspace_name or "Sin workspace / No workspace"
        color = workspace_color or "#6B7280"

        super().__init__(
            bgcolor=ft.Colors.GREY_100,
            border=ft.Border.all(1, ft.Colors.GREY_300),
            border_radius=12,
            padding=10,
            ink=True,
            on_click=on_click,
            content=ft.Row(
                controls=[
                    ft.Container(
                        width=10,
                        height=10,
                        border_radius=999,
                        bgcolor=color,
                    ),
                    ft.Text(
                        label,
                        size=13,
                        weight=ft.FontWeight.W_600,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                ],
                spacing=8,
                tight=True,
            ),
        )
