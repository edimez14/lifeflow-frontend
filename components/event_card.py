from __future__ import annotations

from datetime import datetime

import flet as ft


class EventCard(ft.Container):
    """Card that shows event details with edit and delete buttons."""

    def __init__(
        self,
        event: dict,
        cal_colors: dict[str, str] | None = None,
        on_edit: callable | None = None,
        on_delete: callable | None = None,
    ) -> None:
        self.event = event
        self.cal_colors = cal_colors or {}
        self._on_edit = on_edit
        self._on_delete = on_delete

        title = event.get("title", "Sin título")
        start = datetime.fromisoformat(event["start_datetime"])
        end = datetime.fromisoformat(event["end_datetime"])
        time_str = f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')}"
        color = event.get("color") or self.cal_colors.get(
            event.get("calendar_id"), "#2196F3")

        # Build the card content
        self._title_text = ft.Text(title, weight=ft.FontWeight.BOLD, size=14)
        self._time_text = ft.Text(time_str, size=12)
        self._category_text = ft.Text(
            event.get("category") or "", size=10, italic=True)

        info_column = ft.Column(
            [self._title_text, self._time_text, self._category_text], spacing=2, tight=True)

        edit_btn = ft.IconButton(
            icon=ft.icons.EDIT, icon_size=16, on_click=lambda e: self._on_edit_click())
        delete_btn = ft.IconButton(
            icon=ft.icons.DELETE, icon_size=16, on_click=lambda e: self._on_delete_click())
        actions = ft.Row([edit_btn, delete_btn], spacing=0,
                         alignment=ft.MainAxisAlignment.END)

        # Assemble the card with a left color accent bar
        left_bar = ft.Container(width=4, bgcolor=color,
                                border_radius=ft.BorderRadius(2, 0, 0, 2))
        card_content = ft.Row(
            [
                left_bar,
                ft.Container(info_column, expand=True,
                             padding=ft.padding.only(left=8, right=4)),
                actions,
            ],
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        super().__init__(
            content=card_content,
            padding=0,
            border=ft.border.all(1, ft.colors.GREY_300),
            border_radius=5,
            bgcolor=ft.colors.GREY_50,
            margin=ft.margin.only(bottom=6),
        )

    def _on_edit_click(self) -> None:
        if self._on_edit:
            self._on_edit(self.event)

    def _on_delete_click(self) -> None:
        if self._on_delete:
            self._on_delete(self.event)
