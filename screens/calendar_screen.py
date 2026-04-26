from __future__ import annotations

import calendar
from datetime import datetime, timedelta

import flet as ft

from api.calendar_api import fetch_calendars, fetch_events
from state.app_state import app_state


HOUR_HEIGHT = 60  # pixels per hour in daily view


class CalendarScreen:
    """Calendar screen with monthly, weekly and daily views."""

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.selected_date: datetime | None = None

        today = datetime.now()
        self.current_year = today.year
        self.current_month = today.month

        # For week view
        self.current_week_start = today - timedelta(days=today.weekday())
        # For day view
        self.current_daily_date = today

        self.current_view = "month"  # "month", "week" or "day"

        # UI controls
        self.month_label = ft.Text(size=18, weight=ft.FontWeight.BOLD)
        self.week_label = ft.Text(size=18, weight=ft.FontWeight.BOLD)
        self.day_label = ft.Text(size=18, weight=ft.FontWeight.BOLD)
        self.grid = ft.Column(spacing=2)
        self.detail_panel = ft.Column(visible=False, width=250)

        self.view = self._build_view()

    def _build_view(self) -> ft.Control:
        """Build the full calendar layout with view switcher."""
        # View switcher buttons
        month_btn = ft.ElevatedButton(
            "Mes", on_click=lambda e: self._switch_view("month"))
        week_btn = ft.ElevatedButton(
            "Semana", on_click=lambda e: self._switch_view("week"))
        day_btn = ft.ElevatedButton(
            "Día", on_click=lambda e: self._switch_view("day"))
        view_selector = ft.Row(
            [month_btn, week_btn, day_btn], alignment=ft.MainAxisAlignment.CENTER)

        # Navigation controls depend on active view
        self.nav_controls = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        self._update_nav_controls()

        header = ft.Column([view_selector, self.nav_controls])

        body = ft.Row(
            [self.grid, ft.VerticalDivider(), self.detail_panel],
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        return ft.Column([header, body], expand=True)

    def _switch_view(self, view: str) -> None:
        """Switch between monthly, weekly and daily views."""
        self.current_view = view
        # Reset navigation to today when entering day view for the first time
        if view == "day" and self.current_daily_date is None:
            self.current_daily_date = datetime.now()
        self._update_nav_controls()
        self.page.run_task(self._load_data)

    def _update_nav_controls(self) -> None:
        """Set navigation buttons according to current view."""
        if self.current_view == "month":
            prev_btn = ft.IconButton(
                icon=ft.icons.CHEVRON_LEFT, on_click=self._prev_month)
            next_btn = ft.IconButton(
                icon=ft.icons.CHEVRON_RIGHT, on_click=self._next_month)
            self.nav_controls.controls = [prev_btn, self.month_label, next_btn]
        elif self.current_view == "week":
            prev_btn = ft.IconButton(
                icon=ft.icons.CHEVRON_LEFT, on_click=self._prev_week)
            next_btn = ft.IconButton(
                icon=ft.icons.CHEVRON_RIGHT, on_click=self._next_week)
            self.nav_controls.controls = [prev_btn, self.week_label, next_btn]
        else:  # day
            prev_btn = ft.IconButton(
                icon=ft.icons.CHEVRON_LEFT, on_click=self._prev_day)
            next_btn = ft.IconButton(
                icon=ft.icons.CHEVRON_RIGHT, on_click=self._next_day)
            self.nav_controls.controls = [prev_btn, self.day_label, next_btn]

    async def _prev_month(self, e: ft.ControlEvent) -> None:
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        await self._load_data()

    async def _next_month(self, e: ft.ControlEvent) -> None:
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        await self._load_data()

    async def _prev_week(self, e: ft.ControlEvent) -> None:
        self.current_week_start -= timedelta(weeks=1)
        await self._load_data()

    async def _next_week(self, e: ft.ControlEvent) -> None:
        self.current_week_start += timedelta(weeks=1)
        await self._load_data()

    async def _prev_day(self, e: ft.ControlEvent) -> None:
        self.current_daily_date -= timedelta(days=1)
        await self._load_data()

    async def _next_day(self, e: ft.ControlEvent) -> None:
        self.current_daily_date += timedelta(days=1)
        await self._load_data()

    async def _load_data(self) -> None:
        """Update header label and trigger async reload."""
        if self.current_view == "month":
            self.month_label.value = f"{calendar.month_name[self.current_month]} {self.current_year}"
        elif self.current_view == "week":
            start = self.current_week_start
            end = start + timedelta(days=6)
            self.week_label.value = f"{start.strftime('%d %b')} - {end.strftime('%d %b %Y')}"
        else:  # day
            self.day_label.value = self.current_daily_date.strftime(
                "%A, %d %B %Y")
        self.page.run_task(self._async_load)

    async def _async_load(self) -> None:
        """Async task to load events and build the active view."""
        calendars = await fetch_calendars(app_state.workspace_id)
        cal_colors = {c["id"]: c.get("color", "#2196F3") for c in calendars}

        if self.current_view == "month":
            await self._build_monthly_view(cal_colors)
        elif self.current_view == "week":
            await self._build_weekly_view(cal_colors)
        else:
            await self._build_daily_view(cal_colors)

        self.page.update()

    # ------------------------------------------------------------------
    # Monthly view (unchanged)
    # ------------------------------------------------------------------
    async def _build_monthly_view(self, cal_colors: dict[str, str]) -> None:
        first_day = datetime(self.current_year, self.current_month, 1)
        last_day = first_day.replace(day=calendar.monthrange(
            self.current_year, self.current_month)[1])

        start_of_week = first_day - timedelta(days=first_day.weekday())
        end_of_week = last_day + timedelta(days=6 - last_day.weekday())

        events = await fetch_events(app_state.workspace_id, start_of_week, end_of_week)
        events_by_date: dict[str, list[dict]] = {}
        for ev in events:
            dt = datetime.fromisoformat(ev["start_datetime"]).date()
            key = dt.isoformat()
            events_by_date.setdefault(key, []).append(ev)

        self.grid.controls.clear()

        day_names = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        header_row = ft.Row(
            [ft.Container(ft.Text(name, size=12), width=40,
                          alignment=ft.alignment.center) for name in day_names],
            spacing=2,
        )
        self.grid.controls.append(header_row)

        current = start_of_week
        while current <= end_of_week:
            week_row = ft.Row(spacing=2)
            for _ in range(7):
                day_container = self._build_day_cell(
                    current, events_by_date, first_day, last_day, cal_colors)
                week_row.controls.append(day_container)
                current += timedelta(days=1)
            self.grid.controls.append(week_row)

    # ------------------------------------------------------------------
    # Weekly view (unchanged)
    # ------------------------------------------------------------------
    async def _build_weekly_view(self, cal_colors: dict[str, str]) -> None:
        start = self.current_week_start
        end = start + timedelta(days=6, hours=23, minutes=59, seconds=59)

        events = await fetch_events(app_state.workspace_id, start, end)

        events_by_day: dict[datetime, list[dict]] = {}
        for ev in events:
            dt = datetime.fromisoformat(ev["start_datetime"])
            day_date = dt.replace(hour=0, minute=0, second=0, microsecond=0)
            events_by_day.setdefault(day_date, []).append(ev)

        self.grid.controls.clear()

        hours = list(range(0, 24))
        days_of_week = [start + timedelta(days=i) for i in range(7)]
        day_headers = [ft.Container(ft.Text(day.strftime("%a %d"), size=12, text_align=ft.TextAlign.CENTER),
                                    width=100, alignment=ft.alignment.center) for day in days_of_week]

        empty_corner = ft.Container(width=50)
        header_row = ft.Row([empty_corner] + day_headers, spacing=2,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER)
        self.grid.controls.append(header_row)

        for hour in hours:
            hour_label = ft.Container(
                ft.Text(f"{hour:02d}:00", size=10),
                width=50,
                alignment=ft.alignment.center_right,
                padding=ft.padding.only(right=5),
            )
            cells = []
            for day in days_of_week:
                cell = self._build_hour_cell(
                    day, hour, events_by_day.get(day, []), cal_colors)
                cells.append(cell)
            row = ft.Row([hour_label] + cells, spacing=2)
            self.grid.controls.append(row)

    # ------------------------------------------------------------------
    # Daily view
    # ------------------------------------------------------------------
    async def _build_daily_view(self, cal_colors: dict[str, str]) -> None:
        """Build daily view: hour column on left, event blocks on right as positioned containers."""
        selected_day = self.current_daily_date
        day_start = selected_day.replace(hour=0, minute=0, second=0)
        day_end = selected_day.replace(hour=23, minute=59, second=59)

        events = await fetch_events(app_state.workspace_id, day_start, day_end)

        self.grid.controls.clear()

        # Base grid: rows of hour labels and empty slots
        hour_labels = []
        for hour in range(24):
            row = ft.Row(
                [
                    ft.Container(
                        ft.Text(f"{hour:02d}:00", size=10),
                        width=50,
                        alignment=ft.alignment.center_right,
                        padding=ft.padding.only(right=5),
                    ),
                    ft.Container(
                        border=ft.border.only(
                            bottom=ft.border.BorderSide(1, ft.colors.GREY_200)),
                        expand=True,
                        height=HOUR_HEIGHT,
                    ),
                ],
                spacing=0,
                height=HOUR_HEIGHT,
            )
            hour_labels.append(row)

        # Overlay: event blocks as absolute positioned containers
        event_blocks = []
        for ev in events:
            start = datetime.fromisoformat(ev["start_datetime"])
            end = datetime.fromisoformat(ev["end_datetime"])
            # Calculate position and height
            start_hour = start.hour + start.minute / 60.0
            end_hour = end.hour + end.minute / 60.0
            # at least 15 mins visible
            duration_hours = max(end_hour - start_hour, 0.25)

            top = start_hour * HOUR_HEIGHT
            height = duration_hours * HOUR_HEIGHT
            color = ev.get("color") or cal_colors.get(
                ev["calendar_id"], "#2196F3")
            block = ft.Container(
                content=ft.Text(
                    ev["title"],
                    size=12,
                    color=ft.colors.WHITE,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    max_lines=2,
                ),
                bgcolor=color,
                padding=4,
                border_radius=4,
                left=60,  # after hour label column width
                top=top,
                width=250,  # fixed width for now
                height=height,
            )
            event_blocks.append(block)

        # Use a Stack to overlay the blocks on top of the hour grid
        stack = ft.Stack(
            controls=hour_labels + event_blocks,
            expand=True,
        )
        self.grid.controls.append(stack)

    # ------------------------------------------------------------------
    # Helper for weekly view hour cell (unchanged)
    # ------------------------------------------------------------------
    def _build_hour_cell(self, day: datetime, hour: int, events: list[dict], cal_colors: dict[str, str]) -> ft.Container:
        cell_width = 100
        cell_height = 40
        cell_border = ft.border.all(1, ft.colors.GREY_200)

        hour_start = day.replace(hour=hour, minute=0, second=0)
        hour_end = hour_start + timedelta(hours=1)

        overlapping_events = []
        for ev in events:
            ev_start = datetime.fromisoformat(ev["start_datetime"])
            ev_end = datetime.fromisoformat(ev["end_datetime"])
            if ev_start < hour_end and ev_end > hour_start:
                overlapping_events.append(ev)

        if not overlapping_events:
            return ft.Container(border=cell_border, width=cell_width, height=cell_height)

        blocks = []
        for ev in overlapping_events[:2]:
            color = ev.get("color") or cal_colors.get(
                ev["calendar_id"], "#2196F3")
            title = ev["title"][:5]
            block = ft.Container(
                ft.Text(title, size=8, color=ft.colors.WHITE),
                bgcolor=color,
                padding=2,
                border_radius=2,
                expand=True,
            )
            blocks.append(block)

        return ft.Container(
            ft.Row(blocks, spacing=1),
            border=cell_border,
            width=cell_width,
            height=cell_height,
            padding=1,
        )

    # ------------------------------------------------------------------
    # Day cell for monthly view (unchanged)
    # ------------------------------------------------------------------
    def _build_day_cell(self, date: datetime, events_by_date: dict[str, list[dict]], first: datetime, last: datetime, cal_colors: dict[str, str]) -> ft.Container:
        is_current = first <= date <= last
        text_color = ft.colors.BLACK if is_current else ft.colors.GREY_400
        bg_color = ft.colors.WHITE if is_current else ft.colors.GREY_100

        date_key = date.date().isoformat()
        day_events = events_by_date.get(date_key, [])

        day_number = ft.Text(str(date.day), size=14, color=text_color,
                             weight=ft.FontWeight.BOLD if is_current else ft.FontWeight.NORMAL)

        event_labels = []
        for ev in day_events[:3]:
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

        cell = ft.Container(
            ft.Column([day_number, *event_labels], spacing=1, tight=True,
                      horizontal_alignment=ft.CrossAxisAlignment.START),
            padding=4,
            bgcolor=bg_color,
            border=ft.border.all(1, ft.colors.GREY_300),
            border_radius=4,
            width=90,
            height=90,
            on_click=lambda e, d=date: self._on_day_click(d, events_by_date),
        )
        return cell

    def _on_day_click(self, date: datetime, events_by_date: dict[str, list[dict]]) -> None:
        date_key = date.date().isoformat()
        day_events = events_by_date.get(date_key, [])
        self.selected_date = date
        self._show_detail_panel(date, day_events)

    def _show_detail_panel(self, date: datetime, events: list[dict]) -> None:
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
