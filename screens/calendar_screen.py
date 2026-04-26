from __future__ import annotations

import calendar
from datetime import datetime, timedelta

import flet as ft

from api.calendar_api import fetch_calendars, fetch_events
from state.app_state import app_state


class CalendarScreen:
    """Monthly calendar screen with event labels and day detail panel."""

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.selected_date: datetime | None = None

        # Current viewed month/year
        today = datetime.now()
        self.current_year = today.year
        self.current_month = today.month

        # UI controls
        self.month_label = ft.Text(size=18, weight=ft.FontWeight.BOLD)
        self.grid = ft.Column(spacing=2)

        # Side panel for selected day events
        self.detail_panel = ft.Column(visible=False, width=250)

        self.view = self._build_view()

    def _build_view(self) -> ft.Control:
        """Build the full calendar layout."""
        # Header with navigation
        prev_btn = ft.IconButton(
            icon=ft.icons.CHEVRON_LEFT, on_click=self._prev_month)
        next_btn = ft.IconButton(
            icon=ft.icons.CHEVRON_RIGHT, on_click=self._next_month)
        header = ft.Row(
            [prev_btn, self.month_label, next_btn],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        # Main area: grid + detail panel
        body = ft.Row(
            [self.grid, ft.VerticalDivider(), self.detail_panel],
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        return ft.Column([header, body], expand=True)

    async def _prev_month(self, e: ft.ControlEvent) -> None:
        """Go to previous month."""
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        await self._load_data()

    async def _next_month(self, e: ft.ControlEvent) -> None:
        """Go to next month."""
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        await self._load_data()

    async def _load_data(self) -> None:
        """Fetch events and rebuild the grid."""
        self.month_label.value = f"{calendar.month_name[self.current_month]} {self.current_year}"
        self.page.run_task(self._async_load)

    async def _async_load(self) -> None:
        """Async task to load events and update UI."""
        # Fetch calendars to get colors
        calendars = await fetch_calendars(app_state.workspace_id)
        cal_colors = {c["id"]: c.get("color", "#2196F3") for c in calendars}

        # Compute start and end of month range
        first_day = datetime(self.current_year, self.current_month, 1)
        last_day = first_day.replace(day=calendar.monthrange(
            self.current_year, self.current_month)[1])

        # Extend range to include days from previous/next month visible in grid
        start_of_week = first_day - timedelta(days=first_day.weekday())
        end_of_week = last_day + timedelta(days=6 - last_day.weekday())

        events = await fetch_events(app_state.workspace_id, start_of_week, end_of_week)

        # Group events by date string (YYYY-MM-DD)
        events_by_date: dict[str, list[dict]] = {}
        for ev in events:
            dt = datetime.fromisoformat(ev["start_datetime"]).date()
            key = dt.isoformat()
            events_by_date.setdefault(key, []).append(ev)

        # Build grid
        self.grid.controls.clear()
        # Day headers
        day_names = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        header_row = ft.Row(
            [ft.Container(ft.Text(name, size=12), width=40,
                          alignment=ft.alignment.center) for name in day_names],
            spacing=2,
        )
        self.grid.controls.append(header_row)

        # Build weeks
        current = start_of_week
        while current <= end_of_week:
            week_row = ft.Row(spacing=2)
            for _ in range(7):
                day_container = self._build_day_cell(
                    current, events_by_date, first_day, last_day, cal_colors)
                week_row.controls.append(day_container)
                current += timedelta(days=1)
            self.grid.controls.append(week_row)

        self.page.update()

    def _build_day_cell(self, date: datetime, events_by_date: dict[str, list[dict]], first: datetime, last: datetime, cal_colors: dict[str, str]) -> ft.Container:
        """Build one day cell with number and event labels."""
        is_current = first <= date <= last
        text_color = ft.colors.BLACK if is_current else ft.colors.GREY_400
        bg_color = ft.colors.WHITE if is_current else ft.colors.GREY_100

        date_key = date.date().isoformat()
        day_events = events_by_date.get(date_key, [])

        # Day number
        day_number = ft.Text(str(date.day), size=14, color=text_color,
                             weight=ft.FontWeight.BOLD if is_current else ft.FontWeight.NORMAL)

        # Event labels (colored dots or mini badges)
        event_labels = []
        for ev in day_events[:3]:  # show max 3 labels
            color = ev.get("color") or cal_colors.get(
                ev["calendar_id"], "#2196F3")
            label = ft.Container(
                ft.Text(ev["title"][:10], size=10, color=ft.colors.WHITE),
                bgcolor=color,
                padding=2,
                border_radius=3,
                margin=ft.margin.only(top=1),
            )
            event_labels.append(label)
        if len(day_events) > 3:
            event_labels.append(
                ft.Text(f"+{len(day_events)-3}", size=10, color=ft.colors.GREY_600))

        # Container for day cell, clickable
        cell = ft.Container(
            ft.Column([day_number, *event_labels], spacing=1, tight=True,
                      horizontal_alignment=ft.CrossAxisAlignment.START),
            padding=4,
            bgcolor=bg_color,
            border=ft.border.all(1, ft.colors.GREY_300),
            border_radius=4,
            width=90,  # Adjust width as needed
            height=90,
            on_click=lambda e, d=date: self._on_day_click(d, events_by_date),
        )
        return cell

    def _on_day_click(self, date: datetime, events_by_date: dict[str, list[dict]]) -> None:
        """Handle day click: show detail panel with events."""
        date_key = date.date().isoformat()
        day_events = events_by_date.get(date_key, [])
        self.selected_date = date
        self._show_detail_panel(date, day_events)

    def _show_detail_panel(self, date: datetime, events: list[dict]) -> None:
        """Build and display the side panel for a selected day."""
        self.detail_panel.controls.clear()
        self.detail_panel.controls.append(ft.Text(
            f"{date.day} de {calendar.month_name[date.month]}", weight=ft.FontWeight.BOLD))
        if not events:
            self.detail_panel.controls.append(
                ft.Text("Sin eventos", italic=True))
        else:
            for ev in events:
                title = ev["title"]
                start = datetime.fromisoformat(ev["start_datetime"])
                end = datetime.fromisoformat(ev["end_datetime"])
                time_str = f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')}"
                self.detail_panel.controls.append(
                    ft.Container(
                        ft.Column([
                            ft.Text(title, weight=ft.FontWeight.BOLD),
                            ft.Text(time_str, size=12),
                        ]),
                        padding=4,
                        border_radius=4,
                        bgcolor=ft.colors.GREY_100,
                        margin=ft.margin.only(bottom=4),
                    )
                )
        self.detail_panel.visible = True
        self.page.update()
