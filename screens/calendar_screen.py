from __future__ import annotations

import calendar
from datetime import datetime, timedelta

import flet as ft

from api.calendar_api import (
    fetch_calendars,
    fetch_events,
    create_event,
    update_event,
    delete_event,
    create_calendar,
    fetch_event_categories,
)
from api.monthly_goals_api import (
    create_monthly_goal,
    update_monthly_goal,
    list_all_monthly_goals,
    delete_monthly_goal as delete_goal_api,
)
from components.event_card import EventCard
from state.app_state import app_state
from state.ws_client import register_handler, unregister_handler


HOUR_HEIGHT = 60


class CalendarScreen:
    """Pantalla de calendario con vistas mensual, semanal, diaria y anual."""

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.selected_date: datetime | None = None

        today = datetime.now()
        self.current_year = today.year
        self.current_month = today.month

        self.current_week_start = today - timedelta(days=today.weekday())
        self.current_daily_date = today
        self.current_annual_year = today.year

        self.current_view = "month"

        # Cache de eventos del mes para el panel de detalle
        self._events_by_date: dict[str, list[dict]] = {}

        # UI controls
        self.month_label = ft.Text(size=18, weight=ft.FontWeight.BOLD)
        self.week_label = ft.Text(size=18, weight=ft.FontWeight.BOLD)
        self.day_label = ft.Text(size=18, weight=ft.FontWeight.BOLD)
        self.year_label = ft.Text(size=18, weight=ft.FontWeight.BOLD)
        self.grid = ft.Column(spacing=2, expand=True)
        self.detail_panel = ft.Column(
            visible=False, width=280, scroll=ft.ScrollMode.AUTO
        )
        self.detail_divider = ft.VerticalDivider(visible=False)

        self.goals_btn = ft.IconButton(
            icon=ft.Icons.FLAG,
            tooltip="Objetivos del mes",
            on_click=lambda e: self.page.run_task(self._open_monthly_goals),
        )

        self.view = self._build_view()
        self._register_ws_handlers()

    def _register_ws_handlers(self) -> None:
        async def on_event_created(data: dict) -> None:
            await self._load_data()

        async def on_event_updated(data: dict) -> None:
            await self._load_data()

        async def on_event_deleted(data: dict) -> None:
            await self._load_data()

        register_handler("event.created", on_event_created)
        register_handler("event.updated", on_event_updated)
        register_handler("event.deleted", on_event_deleted)

    def dispose(self) -> None:
        unregister_handler("event.created")
        unregister_handler("event.updated")
        unregister_handler("event.deleted")

    def _build_view(self) -> ft.Control:
        month_btn = ft.Button(
            "Mes", on_click=lambda e: self._switch_view("month"))
        week_btn = ft.Button(
            "Semana", on_click=lambda e: self._switch_view("week"))
        day_btn = ft.Button("Dia", on_click=lambda e: self._switch_view("day"))
        year_btn = ft.Button(
            "Año", on_click=lambda e: self._switch_view("year"))
        view_selector = ft.Row(
            [month_btn, week_btn, day_btn, year_btn],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8,
        )

        self.nav_controls = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        self._update_nav_controls()

        header = ft.Column(
            [view_selector, self.nav_controls],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6,
        )

        body = ft.Row(
            [self.grid, self.detail_divider, self.detail_panel],
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.START,
            alignment=ft.MainAxisAlignment.CENTER,
        )

        return ft.Column([header, body], expand=True, spacing=12)

    def _switch_view(self, view: str) -> None:
        self.current_view = view
        if view == "day" and self.current_daily_date is None:
            self.current_daily_date = datetime.now()
        if view == "year":
            self.current_annual_year = self.current_year
        self._hide_detail_panel()
        self._update_nav_controls()
        self.page.run_task(self._load_data)

    def _update_nav_controls(self) -> None:
        if self.current_view == "month":
            prev_btn = ft.IconButton(
                icon=ft.Icons.CHEVRON_LEFT, on_click=self._prev_month)
            next_btn = ft.IconButton(
                icon=ft.Icons.CHEVRON_RIGHT, on_click=self._next_month)
            month_header = ft.Row(
                [self.month_label, self.goals_btn], spacing=5)
            self.nav_controls.controls = [prev_btn, month_header, next_btn]
        elif self.current_view == "week":
            prev_btn = ft.IconButton(
                icon=ft.Icons.CHEVRON_LEFT, on_click=self._prev_week)
            next_btn = ft.IconButton(
                icon=ft.Icons.CHEVRON_RIGHT, on_click=self._next_week)
            self.nav_controls.controls = [prev_btn, self.week_label, next_btn]
        else:
            prev_btn = ft.IconButton(
                icon=ft.Icons.CHEVRON_LEFT, on_click=self._prev_day)
            next_btn = ft.IconButton(
                icon=ft.Icons.CHEVRON_RIGHT, on_click=self._next_day)
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

    async def _prev_year(self, e: ft.ControlEvent) -> None:
        self.current_annual_year -= 1
        await self._load_data()

    async def _next_year(self, e: ft.ControlEvent) -> None:
        self.current_annual_year += 1
        await self._load_data()

    async def _load_data(self) -> None:
        if self.current_view == "month":
            self.month_label.value = f"{calendar.month_name[self.current_month]} {self.current_year}"
        elif self.current_view == "week":
            start = self.current_week_start
            end = start + timedelta(days=6)
            self.week_label.value = f"{start.strftime('%d %b')} - {end.strftime('%d %b %Y')}"
        elif self.current_view == "day":
            self.day_label.value = self.current_daily_date.strftime(
                "%A, %d %B %Y")
        else:
            self.year_label.value = str(self.current_annual_year)
        self.page.run_task(self._async_load)

    async def _async_load(self) -> None:
        calendars = await fetch_calendars(app_state.workspace_id)
        cal_colors = {c["id"]: c.get("color", "#2196F3") for c in calendars}

        if self.current_view == "month":
            await self._build_monthly_view(cal_colors)
        elif self.current_view == "week":
            await self._build_weekly_view(cal_colors)
        elif self.current_view == "day":
            await self._build_daily_view(cal_colors)
        else:
            await self._build_annual_view(cal_colors)

        self.page.update()

    # ------------------------------------------------------------------
    # Monthly view
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

        self._events_by_date = events_by_date

        self.grid.controls.clear()

        day_names = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]
        header_row = ft.Row(
            [
                ft.Container(
                    ft.Text(name, size=12, text_align=ft.TextAlign.CENTER),
                    alignment=ft.Alignment(0, 0),
                    padding=4,
                    expand=1,
                )
                for name in day_names
            ],
            spacing=6,
            alignment=ft.MainAxisAlignment.CENTER,
            expand=True,
        )
        self.grid.controls.append(header_row)

        current = start_of_week
        while current <= end_of_week:
            week_row = ft.Row(spacing=6, expand=True,
                              alignment=ft.MainAxisAlignment.CENTER)
            for _ in range(7):
                day_container = self._build_day_cell(
                    current, events_by_date, first_day, last_day, cal_colors)
                week_row.controls.append(day_container)
                current += timedelta(days=1)
            self.grid.controls.append(week_row)

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
        day_headers = [
            ft.Container(
                ft.Text(day.strftime("%a %d"), size=12,
                        text_align=ft.TextAlign.CENTER),
                alignment=ft.Alignment(0, 0),
                padding=4,
                expand=1,
            )
            for day in days_of_week
        ]

        empty_corner = ft.Container(width=50)
        header_row = ft.Row(
            [empty_corner] + day_headers,
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )
        self.grid.controls.append(header_row)

        for hour in hours:
            hour_label = ft.Container(
                ft.Text(f"{hour:02d}:00", size=10),
                width=50,
                alignment=ft.Alignment(0, 0.5),
                padding=ft.Padding.only(right=5),
            )
            cells = []
            for day in days_of_week:
                cell = self._build_hour_cell(
                    day, hour, events_by_day.get(day, []), cal_colors)
                cells.append(cell)
            row = ft.Row([hour_label] + cells, spacing=6, expand=True)
            self.grid.controls.append(row)

    async def _build_daily_view(self, cal_colors: dict[str, str]) -> None:
        selected_day = self.current_daily_date
        day_start = selected_day.replace(hour=0, minute=0, second=0)
        day_end = selected_day.replace(hour=23, minute=59, second=59)

        events = await fetch_events(app_state.workspace_id, day_start, day_end)

        self.grid.controls.clear()

        hour_labels = []
        for hour in range(24):
            row = ft.Row(
                [
                    ft.Container(
                        ft.Text(f"{hour:02d}:00", size=10),
                        width=50,
                        alignment=ft.Alignment(1, 0.5),
                        padding=ft.Padding.only(right=5),
                    ),
                    ft.Container(
                        border=ft.Border.only(
                            bottom=ft.BorderSide(1, ft.Colors.GREY_200)),
                        expand=True,
                        height=HOUR_HEIGHT,
                    ),
                ],
                spacing=0,
                height=HOUR_HEIGHT,
            )
            hour_labels.append(row)

        event_blocks = []
        for ev in events:
            start_dt = datetime.fromisoformat(ev["start_datetime"])
            end_dt = datetime.fromisoformat(ev["end_datetime"])
            start_hour = start_dt.hour + start_dt.minute / 60.0
            end_hour = end_dt.hour + end_dt.minute / 60.0
            duration_hours = max(end_hour - start_hour, 0.25)

            top = start_hour * HOUR_HEIGHT
            height = duration_hours * HOUR_HEIGHT
            color = ev.get("color") or cal_colors.get(
                ev["calendar_id"], "#2196F3")
            block = ft.Container(
                content=ft.Text(
                    ev["title"],
                    size=12,
                    color=ft.Colors.WHITE,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    max_lines=2,
                ),
                bgcolor=color,
                padding=4,
                border_radius=4,
                left=60,
                top=top,
                width=250,
                height=height,
            )
            event_blocks.append(block)

        stack = ft.Stack(controls=hour_labels + event_blocks, expand=True)
        self.grid.controls.append(stack)

    async def _build_annual_view(self, cal_colors: dict[str, str]) -> None:
        year = self.current_annual_year
        start_dt = datetime(year, 1, 1)
        end_dt = datetime(year, 12, 31, 23, 59, 59)

        events = await fetch_events(app_state.workspace_id, start_dt, end_dt)
        events_by_date: dict[tuple[int, int], list[dict]] = {}
        for ev in events:
            dt = datetime.fromisoformat(ev["start_datetime"])
            key = (dt.month, dt.day)
            events_by_date.setdefault(key, []).append(ev)

        self.grid.controls.clear()
        self.grid.scroll = None

        months = []
        for month in range(1, 13):
            month_container = self._build_mini_month(
                year, month, events_by_date, cal_colors)
            months.append(month_container)

        rows = []
        for i in range(0, 12, 4):
            row = ft.Row(
                months[i:i + 4],
                spacing=14,
                alignment=ft.MainAxisAlignment.CENTER,
                expand=True,
            )
            rows.append(row)
        self.grid.controls.extend(rows)

    def _build_mini_month(self, year: int, month: int, events_by_date: dict[tuple[int, int], list[dict]], cal_colors: dict[str, str]) -> ft.Container:
        month_name = calendar.month_name[month]
        cal_data = calendar.monthcalendar(year, month)

        day_headers = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sa", "Do"]
        header_row = ft.Row(
            [ft.Text(h, size=8, text_align=ft.TextAlign.CENTER, width=18)
             for h in day_headers],
            spacing=1,
            alignment=ft.MainAxisAlignment.CENTER,
        )

        week_rows = []
        for week in cal_data:
            day_cells = []
            for day in week:
                if day == 0:
                    cell = ft.Container(width=18, height=18)
                else:
                    event_list = events_by_date.get((month, day), [])
                    dot = None
                    if event_list:
                        ev = event_list[0]
                        dot_color = ev.get("color") or cal_colors.get(
                            ev["calendar_id"], "#2196F3")
                        dot = ft.Container(
                            width=5, height=5, bgcolor=dot_color, border_radius=ft.BorderRadius(5, 5, 5, 5),
                        )

                    day_date = datetime(year, month, day)
                    captured_day = day_date
                    cell = ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(str(day), size=9,
                                        text_align=ft.TextAlign.CENTER),
                                dot if dot else ft.Container(height=5),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=1,
                            tight=True,
                        ),
                        width=22,
                        height=28,
                        alignment=ft.Alignment(0, 0),
                        on_click=lambda e, d=captured_day: self._on_annual_day_click(
                            d),
                    )
                day_cells.append(cell)
            week_row = ft.Row(day_cells, spacing=1,
                              alignment=ft.MainAxisAlignment.CENTER)
            week_rows.append(week_row)

        month_title = ft.Container(
            content=ft.Text(
                month_name, size=11, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
            alignment=ft.Alignment(0, 0),
            padding=2,
            ink=True,
            on_click=lambda e, y=year, m=month: self._on_annual_month_click(
                y, m),
        )

        content = ft.Column(
            [month_title, header_row, *week_rows],
            spacing=2,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        return ft.Container(
            content=content,
            padding=8,
            border=ft.Border.all(1, ft.Colors.GREY_300),
            border_radius=5,
            width=190,
            height=205,
        )

    def _on_annual_day_click(self, date: datetime) -> None:
        self.current_daily_date = date
        self._switch_view("day")

    def _on_annual_month_click(self, year: int, month: int) -> None:
        self.current_year = year
        self.current_month = month
        self._switch_view("month")

    def _build_hour_cell(self, day: datetime, hour: int, events: list[dict], cal_colors: dict[str, str]) -> ft.Container:
        cell_height = 44
        cell_border = ft.Border.all(1, ft.Colors.GREY_200)

        hour_start = day.replace(hour=hour, minute=0, second=0)
        hour_end = hour_start + timedelta(hours=1)

        overlapping_events = []
        for ev in events:
            ev_start = datetime.fromisoformat(ev["start_datetime"])
            ev_end = datetime.fromisoformat(ev["end_datetime"])
            if ev_start < hour_end and ev_end > hour_start:
                overlapping_events.append(ev)

        if not overlapping_events:
            return ft.Container(border=cell_border, expand=True, height=cell_height)

        blocks = []
        for ev in overlapping_events[:2]:
            color = ev.get("color") or cal_colors.get(
                ev["calendar_id"], "#2196F3")
            title = ev["title"][:5]
            block = ft.Container(
                ft.Text(title, size=8, color=ft.Colors.WHITE),
                bgcolor=color,
                padding=2,
                border_radius=2,
                expand=True,
            )
            blocks.append(block)

        return ft.Container(
            ft.Row(blocks, spacing=1),
            border=cell_border,
            expand=True,
            height=cell_height,
            padding=1,
        )

    # ------------------------------------------------------------------
    # Day cell for monthly view (con eventos visibles)
    # ------------------------------------------------------------------
    def _build_day_cell(self, date: datetime, events_by_date: dict[str, list[dict]], first: datetime, last: datetime, cal_colors: dict[str, str]) -> ft.Container:
        is_current = first <= date <= last
        text_color = ft.Colors.BLACK if is_current else ft.Colors.GREY_400
        bg_color = ft.Colors.WHITE if is_current else ft.Colors.GREY_100

        date_key = date.date().isoformat()
        day_events = events_by_date.get(date_key, [])

        day_number = ft.Text(
            str(date.day), size=14, color=text_color,
            weight=ft.FontWeight.BOLD if is_current else ft.FontWeight.NORMAL,
        )

        # Eventos visibles dentro de la card del dia, con color segun categoria
        CAT_COLORS = {
            "importante": "#FF9800",
            "urgente": "#F44336",
            "especial": "#9C27B0",
            "repetitivo": "#2196F3",
            "solo_una_vez": "#4CAF50",
        }

        event_labels = []
        for ev in day_events[:3]:
            color = ev.get("color") or cal_colors.get(
                ev["calendar_id"], "#2196F3")
            cat = ev.get("category")
            display_color = CAT_COLORS.get(cat, color)
            label = ft.Container(
                ft.Text(ev["title"][:10], size=10, color=ft.Colors.WHITE),
                bgcolor=display_color,
                padding=2,
                border_radius=3,
                margin=ft.margin.Margin(top=1, left=0, right=0, bottom=0),
            )
            event_labels.append(label)

        if len(day_events) > 3:
            event_labels.append(
                ft.Text(f"+{len(day_events)-3}", size=10,
                        color=ft.Colors.GREY_600)
            )

        cell = ft.Container(
            ft.Column(
                [day_number, *event_labels],
                spacing=2,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.START,
            ),
            padding=6,
            bgcolor=bg_color,
            border=ft.Border.all(1, ft.Colors.GREY_300),
            border_radius=6,
            height=110,
            expand=1,
            on_click=lambda e, captured_date=date: self._on_day_click(
                captured_date),
        )
        return cell

    # ------------------------------------------------------------------
    # Detail panel: ver eventos + cerrar + agregar evento
    # ------------------------------------------------------------------
    def _on_day_click(self, date: datetime) -> None:
        date_key = date.date().isoformat()
        day_events = self._events_by_date.get(date_key, [])
        self.selected_date = date
        self._show_detail_panel(date, day_events)

    def _show_detail_panel(self, date: datetime, events: list[dict]) -> None:
        self.detail_panel.controls.clear()

        # Header con titulo y boton cerrar
        header = ft.Row(
            [
                ft.Text(
                    f"{date.day} de {calendar.month_name[date.month]}",
                    weight=ft.FontWeight.BOLD,
                    expand=True,
                ),
                ft.IconButton(
                    icon=ft.Icons.CLOSE,
                    icon_size=20,
                    tooltip="Cerrar",
                    on_click=lambda e: self._hide_detail_panel(),
                ),
            ],
            spacing=0,
        )
        self.detail_panel.controls.append(header)

        # Boton agregar evento
        add_btn = ft.Button(
            "Agregar evento",
            icon=ft.Icons.ADD,
            on_click=lambda e, d=date: self.page.run_task(
                self._open_create_event_modal, d),
        )
        self.detail_panel.controls.append(add_btn)

        # Separador
        self.detail_panel.controls.append(ft.Divider(height=10))

        # Lista de eventos del dia
        if not events:
            self.detail_panel.controls.append(
                ft.Text("Sin eventos", italic=True, size=14))
        else:
            for ev in events:
                card = EventCard(
                    event=ev,
                    cal_colors={},
                    on_edit=lambda e, ev=ev: self.page.run_task(
                        self._edit_event, ev),
                    on_delete=lambda e, ev=ev: self.page.run_task(
                        self._delete_event, ev),
                )
                self.detail_panel.controls.append(card)

        self.detail_panel.visible = True
        self.detail_divider.visible = True
        self.page.update()

    def _hide_detail_panel(self) -> None:
        self.detail_panel.visible = False
        self.detail_divider.visible = False
        self.page.update()

    async def _edit_event(self, event: dict) -> None:
        """Show a dialog to edit an existing event."""
        from datetime import datetime as dt_

        title_f = ft.TextField(label="Titulo", value=event.get("title", ""))
        desc_f = ft.TextField(
            label="Descripcion", multiline=True, min_lines=2, max_lines=4,
            value=event.get("description", ""),
        )

        start = dt_.fromisoformat(event["start_datetime"])
        end = dt_.fromisoformat(event["end_datetime"])
        start_f = ft.TextField(
            label="Hora inicio (HH:MM)",
            value=start.strftime("%H:%M"), width=120,
        )
        end_f = ft.TextField(
            label="Hora fin (HH:MM)",
            value=end.strftime("%H:%M"), width=120,
        )
        color_f = ft.TextField(
            label="Color hex", value=event.get("color", "#2196F3"), width=140,
        )

        contenido = ft.Column([
            ft.Text("Editar evento", weight=ft.FontWeight.BOLD, size=18),
            title_f, desc_f,
            ft.Row([start_f, end_f], spacing=10),
            color_f,
        ], spacing=10, tight=True, scroll=ft.ScrollMode.AUTO, width=350)

        def cerrar_dlg():
            dlg.open = False
            self.page.update()

        async def guardar():
            if not title_f.value:
                title_f.error_text = "Titulo obligatorio"
                self.page.update()
                return
            try:
                date_str = start.date().isoformat()
                sd = dt_.fromisoformat(f"{date_str}T{start_f.value}:00")
                ed = dt_.fromisoformat(f"{date_str}T{end_f.value}:00")
            except Exception:
                title_f.error_text = "Hora invalida (HH:MM)"
                self.page.update()
                return
            data = {
                "title": title_f.value,
                "description": desc_f.value or None,
                "start_datetime": sd.isoformat(),
                "end_datetime": ed.isoformat(),
                "color": color_f.value or None,
                "category": event.get("category"),
                "recurrence_rule": event.get("recurrence_rule"),
            }
            try:
                await update_event(app_state.workspace_id, event["id"], data)
            except Exception as ex:
                title_f.error_text = f"Error: {ex}"
                self.page.update()
                return
            cerrar_dlg()
            await self._load_data()

        dlg = ft.AlertDialog(
            title=ft.Text("Editar evento"),
            content=contenido,
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: cerrar_dlg()),
                ft.Button(
                    "Guardar", on_click=lambda e: self.page.run_task(guardar)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    async def _delete_event(self, event: dict) -> None:
        """Confirm and delete an event."""
        async def confirmar():
            try:
                await delete_event(app_state.workspace_id, event["id"])
            except Exception:
                pass  # silently ignore — WS refresh will update UI
            dlg.open = False
            self.page.update()
            await self._load_data()

        dlg = ft.AlertDialog(
            title=ft.Text("Eliminar evento"),
            content=ft.Text(f"¿Eliminar \"{event.get('title', '')}\"?"),
            actions=[
                ft.TextButton("Cancelar",
                              on_click=lambda e: self._close_dialog_with(dlg)),
                ft.Button("Eliminar",
                          on_click=lambda e: self.page.run_task(confirmar)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _close_dialog(self, e: ft.ControlEvent) -> None:
        """Close the current dialog."""
        if self.page.overlay:
            for ctrl in self.page.overlay:
                if isinstance(ctrl, ft.AlertDialog) and ctrl.open:
                    ctrl.open = False
                    self.page.update()
                    return

    def _close_dialog_with(self, dlg: ft.AlertDialog) -> None:
        """Close a specific dialog."""
        dlg.open = False
        self.page.update()

    # ------------------------------------------------------------------
    # Helpers for recurrence RRULE generation
    # ------------------------------------------------------------------
    def _make_rrule_str(
        self,
        freq: str,
        interval: int,
        by_days: list[str] | None = None,
        by_month_day: int | None = None,
        by_month: int | None = None,
        count: int | None = None,
        until_date: str | None = None,
    ) -> str:
        """Build an iCal RRULE string from user selections."""
        parts = [f"FREQ={freq}"]
        if interval > 1:
            parts.append(f"INTERVAL={interval}")
        if by_days:
            parts.append(f"BYDAY={','.join(by_days)}")
        if by_month_day is not None and freq in ("MONTHLY", "YEARLY"):
            parts.append(f"BYMONTHDAY={by_month_day}")
        if by_month and freq == "YEARLY":
            parts.append(f"BYMONTH={by_month}")
        if count:
            parts.append(f"COUNT={count}")
        elif until_date:
            parts.append(f"UNTIL={until_date.replace('-', '')}T235959Z")
        result = ";".join(parts)
        print(f"[RECURRENCE] _make_rrule_str: {result}")
        return result

    # ------------------------------------------------------------------
    # Modal para crear nuevo evento (AlertDialog)
    # ------------------------------------------------------------------
    async def _open_create_event_modal(self, date: datetime) -> None:
        """Abre un dialogo para crear evento."""
        title_f = ft.TextField(
            label="Titulo", hint_text="Ej: Reunion", autofocus=True)
        desc_f = ft.TextField(label="Descripcion",
                              multiline=True, min_lines=2, max_lines=4)
        start_f = ft.TextField(
            label="Hora inicio (HH:MM)", value="09:00", width=120)
        end_f = ft.TextField(label="Hora fin (HH:MM)",
                             value="10:00", width=120)
        date_str = date.strftime("%Y-%m-%d")

        cals = await fetch_calendars(app_state.workspace_id)

        # Si no hay calendarios, crear uno por defecto
        if not cals:
            try:
                new_cal = await create_calendar(app_state.workspace_id, "Mi calendario", "#2196F3")
                cals = [new_cal]
            except Exception:
                cals = []

        cal_options = [ft.dropdown.Option(
            key=c["id"], text=c["name"]) for c in cals]
        cal_f = ft.Dropdown(
            label="Calendario",
            options=cal_options,
            value=cals[0]["id"] if cals else None,
        )

        try:
            cats = await fetch_event_categories()
        except Exception:
            cats = []

        cat_options = [ft.dropdown.Option(
            key=c.get("value", c.get("name", "")),
            text=c.get("label", c.get("name", ""))
        ) for c in cats] if cats else []
        color_f = ft.TextField(label="Color hex", value="#2196F3", width=140)

        # ---- Recurrence UI (visible only when category == "repetitivo") ----
        freq_options = [
            ft.dropdown.Option("DAILY", "Diario"),
            ft.dropdown.Option("WEEKLY", "Semanal"),
            ft.dropdown.Option("MONTHLY", "Mensual"),
            ft.dropdown.Option("YEARLY", "Anual"),
            ft.dropdown.Option("FECHAS", "Fechas seleccionadas"),
        ]
        # Intervalo (cada N dias/semanas/meses)
        interval_f = ft.TextField(
            label="Cada (n)", value="1", width=80, keyboard_type=ft.KeyboardType.NUMBER)

        # Dias de la semana (semanal) — RRULE requires English abbreviations
        day_names = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
        day_labels = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]
        day_checks: list[ft.Checkbox] = []
        for dn, dl in zip(day_names, day_labels):
            cb = ft.Checkbox(label=dl, value=(
                dn in ("MO", "TU", "WE", "TH", "FR")), width=55)
            day_checks.append(cb)

        # Dia del mes (mensual)
        monthday_f = ft.TextField(label="Dia del mes", value=date.strftime(
            "%d"), width=100, keyboard_type=ft.KeyboardType.NUMBER)

        # Mes (anual)
        month_f = ft.Dropdown(
            label="Mes",
            options=[ft.dropdown.Option(str(i), datetime(
                2000, i, 1).strftime("%B")) for i in range(1, 13)],
            value=str(date.month),
            width=120,
        )
        anual_day_f = ft.TextField(label="Dia", value=date.strftime(
            "%d"), width=80, keyboard_type=ft.KeyboardType.NUMBER)

        # Fin de recurrencia
        end_options = [
            ft.dropdown.Option("COUNT", "Despues de N ocurrencias"),
            ft.dropdown.Option("UNTIL", "Hasta fecha"),
            ft.dropdown.Option("NEVER", "Nunca"),
        ]
        count_f = ft.TextField(label="Ocurrencias", value="10",
                               width=100, keyboard_type=ft.KeyboardType.NUMBER)
        until_f = ft.TextField(label="Hasta (YYYY-MM-DD)",
                               width=140, hint_text="2025-12-31")

        # Fechas seleccionadas
        selected_dates: list[str] = [date_str]
        selected_dates_text = ft.Text(
            f"Fechas: {', '.join(selected_dates)}", size=13)
        date_pick_f = ft.TextField(
            label="Agregar fecha (YYYY-MM-DD)", width=180, hint_text=date_str)

        def add_selected_date(_):
            val = date_pick_f.value.strip() if date_pick_f.value else ""
            if val and val not in selected_dates:
                selected_dates.append(val)
                selected_dates_text.value = f"Fechas: {', '.join(selected_dates)}"
                date_pick_f.value = ""
                print(f"[RECURRENCE] Added date: {val}, total: {len(selected_dates)}")
            self.page.update()

        add_date_btn = ft.Button("Agregar", on_click=add_selected_date)

        # -- Frequency-specific controls container --
        diario_controls = ft.Column([interval_f], spacing=6, visible=True)
        semanal_controls = ft.Column(
            [ft.Text("Dias:", size=13), ft.Row(
                day_checks, spacing=4), interval_f],
            spacing=6, visible=False,
        )
        mensual_controls = ft.Column(
            [monthday_f, interval_f], spacing=6, visible=False)
        anual_controls = ft.Column(
            [month_f, anual_day_f], spacing=6, visible=False)
        fechas_controls = ft.Column(
            [ft.Row([date_pick_f, add_date_btn], spacing=4),
             selected_dates_text],
            spacing=6, visible=False,
        )

        # End condition controls
        count_row = ft.Row([count_f], spacing=6, visible=True)
        until_row = ft.Row([until_f], spacing=6, visible=False)

        def _update_freq_visibility(freq_val: str):
            print(f"[RECURRENCE] Frequency changed to: {freq_val}")
            diario_controls.visible = (freq_val == "DAILY")
            semanal_controls.visible = (freq_val == "WEEKLY")
            mensual_controls.visible = (freq_val == "MONTHLY")
            anual_controls.visible = (freq_val == "YEARLY")
            fechas_controls.visible = (freq_val == "FECHAS")
            show_end = freq_val != "FECHAS"
            end_type_f.visible = show_end
            count_row.visible = show_end and end_type_f.value == "COUNT"
            until_row.visible = show_end and end_type_f.value == "UNTIL"
            self.page.update()

        def _on_freq_change(e):
            _update_freq_visibility(e.control.value)

        freq_f = ft.Dropdown(
            label="Frecuencia",
            options=freq_options,
            value="DAILY",
            width=200,
            on_change=_on_freq_change,
        )

        def _on_end_type_change(e):
            print(f"[RECURRENCE] End type changed to: {e.control.value}")
            count_row.visible = (e.control.value == "COUNT")
            until_row.visible = (e.control.value == "UNTIL")
            self.page.update()

        end_type_f = ft.Dropdown(
            label="Finaliza",
            options=end_options,
            value="COUNT",
            width=200,
            on_change=_on_end_type_change,
        )

        recurrence_section = ft.Container(
            visible=False,
            border=ft.Border.all(1, ft.Colors.GREY_300),
            border_radius=8,
            padding=10,
            content=ft.Column([
                ft.Text("Configuracion de recurrencia",
                        weight=ft.FontWeight.BOLD, size=14),
                freq_f,
                ft.Divider(height=4),
                diario_controls,
                semanal_controls,
                mensual_controls,
                anual_controls,
                fechas_controls,
                ft.Divider(height=4),
                end_type_f,
                count_row,
                until_row,
            ], spacing=8, tight=True),
        )

        def _on_cat_change(e):
            is_repetitivo = (e.control.value == "repetitivo")
            print(f"[RECURRENCE] Category changed to: {e.control.value}, showing recurrence: {is_repetitivo}")
            recurrence_section.visible = is_repetitivo
            self.page.update()

        cat_f = ft.Dropdown(
            label="Categoria",
            options=cat_options,
            value=None,
            on_change=_on_cat_change,
        )

        contenido = ft.Column([
            ft.Text("Nuevo evento", weight=ft.FontWeight.BOLD, size=18),
            title_f, desc_f,
            ft.Row([ft.Text(f"Fecha: {date_str}")], spacing=5),
            ft.Row([start_f, end_f], spacing=10),
            cal_f, cat_f, color_f,
            recurrence_section,
        ], spacing=10, tight=True, scroll=ft.ScrollMode.AUTO, width=380)

        def cerrar_dlg():
            dlg.open = False
            self.page.update()

        async def guardar_evento():
            if not title_f.value:
                title_f.error_text = "Titulo obligatorio"
                self.page.update()
                return
            try:
                sd = datetime.fromisoformat(f"{date_str}T{start_f.value}:00")
                ed = datetime.fromisoformat(f"{date_str}T{end_f.value}:00")
            except Exception:
                title_f.error_text = "Hora invalida (HH:MM)"
                self.page.update()
                return
            if not cal_f.value:
                title_f.error_text = "Selecciona calendario"
                self.page.update()
                return

            cat_val = cat_f.value or None
            # Build RRULE if repetitivo and not fechas
            rrule_str = None
            multiple_events: list[dict] = []
            if cat_val == "repetitivo":
                print(f"[RECURRENCE] Building recurrence rule, freq={freq_f.value}")
                if freq_f.value == "FECHAS":
                    # Create one event per selected date
                    print(f"[RECURRENCE] Creating events for dates: {selected_dates}")
                    for d_str in selected_dates:
                        try:
                            fd = datetime.fromisoformat(
                                f"{d_str}T{start_f.value}:00")
                            fe = datetime.fromisoformat(
                                f"{d_str}T{end_f.value}:00")
                        except Exception as ex:
                            print(f"[RECURRENCE] Error parsing date {d_str}: {ex}")
                            continue
                        multiple_events.append({
                            "calendar_id": cal_f.value,
                            "title": title_f.value,
                            "description": desc_f.value or None,
                            "start_datetime": fd.isoformat(),
                            "end_datetime": fe.isoformat(),
                            "category": cat_val,
                            "color": color_f.value or None,
                            "recurrence_rule": None,
                        })
                    print(f"[RECURRENCE] Created {len(multiple_events)} individual events")
                else:
                    try:
                        interval = int(
                            interval_f.value) if interval_f.value else 1
                    except ValueError:
                        interval = 1
                    if interval < 1:
                        interval = 1

                    by_days = None
                    by_month_day = None
                    by_month = None
                    if freq_f.value == "WEEKLY":
                        selected_days = [day_names[i]
                                         for i, cb in enumerate(day_checks) if cb.value]
                        if selected_days:
                            by_days = selected_days
                        else:
                            by_days = ["MO"]
                        print(f"[RECURRENCE] Weekly on days: {by_days}")
                    elif freq_f.value == "MONTHLY":
                        try:
                            by_month_day = int(monthday_f.value)
                        except ValueError:
                            by_month_day = int(date.strftime("%d"))
                        if by_month_day < 1:
                            by_month_day = 1
                        if by_month_day > 31:
                            by_month_day = 31
                        print(f"[RECURRENCE] Monthly on day: {by_month_day}")
                    elif freq_f.value == "YEARLY":
                        try:
                            by_month = int(
                                month_f.value) if month_f.value else date.month
                        except ValueError:
                            by_month = date.month
                        try:
                            by_month_day = int(anual_day_f.value)
                        except ValueError:
                            by_month_day = int(date.strftime("%d"))
                        print(f"[RECURRENCE] Yearly on month={by_month}, day={by_month_day}")

                    count_val = None
                    until_val = None
                    if end_type_f.value == "COUNT":
                        try:
                            count_val = int(count_f.value)
                        except ValueError:
                            count_val = 10
                        print(f"[RECURRENCE] End after {count_val} occurrences")
                    elif end_type_f.value == "UNTIL" and until_f.value:
                        until_val = until_f.value.strip()
                        print(f"[RECURRENCE] End until date: {until_val}")
                    else:
                        print(f"[RECURRENCE] No end condition (runs forever)")

                    rrule_str = self._make_rrule_str(
                        freq=freq_f.value,
                        interval=interval,
                        by_days=by_days,
                        by_month_day=by_month_day,
                        by_month=by_month,
                        count=count_val,
                        until_date=until_val,
                    )
                    print(f"[RECURRENCE] Generated RRULE: {rrule_str}")

            if multiple_events:
                # Create one event per selected date
                print(f"[RECURRENCE] Sending {len(multiple_events)} individual events to backend")
                for ev_data in multiple_events:
                    try:
                        await create_event(app_state.workspace_id, ev_data)
                        print(f"[RECURRENCE] Created event: {ev_data['title']} on {ev_data['start_datetime']}")
                    except Exception as ex:
                        print(f"[RECURRENCE] Error creating event for fechas: {ex}")
                cerrar_dlg()
                await self._load_data()
                return

            data = {
                "calendar_id": cal_f.value, "title": title_f.value,
                "description": desc_f.value or None,
                "start_datetime": sd.isoformat(), "end_datetime": ed.isoformat(),
                "category": cat_val, "color": color_f.value or None,
                "recurrence_rule": rrule_str,
            }
            print(f"[RECURRENCE] Sending event data: title={data['title']}, category={data['category']}, rrule={data['recurrence_rule']}")
            try:
                await create_event(app_state.workspace_id, data)
                print(f"[RECURRENCE] Event created successfully")
            except Exception as ex:
                print(f"[RECURRENCE] Error creating event: {ex}")
                title_f.error_text = f"Error: {ex}"
                self.page.update()
                return
            cerrar_dlg()
            await self._load_data()

        async def on_guardar(e):
            await guardar_evento()

        dlg = ft.AlertDialog(
            title=ft.Text("Nuevo evento"),
            content=contenido,
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: cerrar_dlg()),
                ft.Button("Guardar", on_click=on_guardar),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    # ------------------------------------------------------------------
    # Monthly goals
    # ------------------------------------------------------------------
    async def _open_monthly_goals(self) -> None:
        """Open a centered dialog to view, create, edit and delete monthly goals."""
        try:
            goals = await list_all_monthly_goals(app_state.workspace_id)
        except Exception as e:
            print(f"Error loading monthly goals: {e}")
            goals = []

        # Form fields for current month (always empty for new input)
        self._goal_text_field = ft.TextField(
            label="Objetivo del mes actual",
            multiline=True,
            min_lines=2,
            max_lines=4,
        )
        self._action_plan_field = ft.TextField(
            label="Plan de accion",
            multiline=True,
            min_lines=2,
            max_lines=4,
        )

        save_btn = ft.Button(
            "Guardar",
            on_click=lambda e: self.page.run_task(
                self._save_goal_from_dialog),
        )

        # Build list of existing goals
        goal_items: list[ft.Control] = []
        for g in goals:
            month_name = calendar.month_name[g["month"]]
            is_completed = g.get("is_completed", False)
            status_icon = ft.Icon(
                ft.Icons.CHECK_CIRCLE if is_completed else ft.Icons.RADIO_BUTTON_UNCHECKED,
                color=ft.Colors.GREEN_400 if is_completed else ft.Colors.GREY_400,
                size=18,
            )
            status_text = ft.Text(
                "Completado" if is_completed else "Pendiente",
                size=12,
                color=ft.Colors.GREEN_400 if is_completed else ft.Colors.GREY_400,
            )
            toggle_btn = ft.IconButton(
                icon=ft.Icons.TOGGLE_ON if is_completed else ft.Icons.TOGGLE_OFF_OUTLINED,
                icon_size=20,
                tooltip="Cambiar estado",
                on_click=lambda e, goal=g: self.page.run_task(
                    self._toggle_goal_status, goal
                ),
            )
            edit_btn = ft.IconButton(
                icon=ft.Icons.EDIT,
                icon_size=18,
                tooltip="Editar",
                on_click=lambda e, goal=g: self.page.run_task(
                    self._edit_existing_goal, goal
                ),
            )
            delete_btn = ft.IconButton(
                icon=ft.Icons.DELETE,
                icon_size=18,
                tooltip="Eliminar",
                on_click=lambda e, goal=g: self.page.run_task(
                    self._delete_existing_goal, goal
                ),
            )
            goal_items.append(
                ft.Container(
                    content=ft.Column([
                        ft.Row(
                            [status_icon, status_text],
                            spacing=4,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Text(
                            f"{month_name} {g['year']}",
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Text(g.get("goal_text", "(sin objetivo)")),
                        ft.Text(
                            g.get("action_plan", ""),
                            size=12,
                            color=ft.Colors.GREY_600,
                        ),
                        ft.Row(
                            [toggle_btn, edit_btn, delete_btn],
                            alignment=ft.MainAxisAlignment.END,
                        ),
                    ]),
                    padding=ft.Padding(top=8, bottom=8, left=0, right=0),
                )
            )
            goal_items.append(ft.Divider(height=1))

        if not goal_items:
            goal_items.append(
                ft.Text(
                    "No hay objetivos guardados",
                    italic=True,
                    color=ft.Colors.GREY_500,
                )
            )

        dlg = ft.AlertDialog(
            title=ft.Text("Objetivos del mes",
                          weight=ft.FontWeight.BOLD, size=18),
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Nuevo objetivo",
                                weight=ft.FontWeight.BOLD, size=14),
                        self._goal_text_field,
                        self._action_plan_field,
                        ft.Row(
                            [save_btn],
                            alignment=ft.MainAxisAlignment.END,
                        ),
                        ft.Divider(height=2),
                        ft.Text("Todos los objetivos",
                                weight=ft.FontWeight.BOLD, size=14),
                        *goal_items,
                    ],
                    spacing=8,
                    scroll=ft.ScrollMode.AUTO,
                ),
                width=480,
                padding=ft.Padding(top=10, bottom=10, left=10, right=10),
            ),
            actions=[
                ft.TextButton(
                    "Cerrar", on_click=self._close_goals_dialog),
            ],
            modal=True,
        )
        self._goals_dlg = dlg
        dlg.open = True
        self.page.overlay.append(dlg)
        self.page.update()

    async def _toggle_goal_status(self, goal: dict) -> None:
        """Toggle a goal between completed and pending."""
        new_status = not goal.get("is_completed", False)
        data = {
            "goal_text": goal["goal_text"],
            "action_plan": goal["action_plan"],
            "is_completed": new_status,
        }
        try:
            await update_monthly_goal(
                app_state.workspace_id, goal["id"], data
            )
        except Exception as ex:
            print(f"Error toggling goal status: {ex}")
        # Close old dialog before reopening with fresh data
        if self._goals_dlg:
            self._goals_dlg.open = False
            self.page.update()
        await self._open_monthly_goals()

    async def _save_goal_from_dialog(self) -> None:
        """Save current month's goal and refresh the dialog."""
        try:
            data = {
                "year": self.current_year,
                "month": self.current_month,
                "goal_text": self._goal_text_field.value or "",
                "action_plan": self._action_plan_field.value or "",
            }
            await create_monthly_goal(app_state.workspace_id, data)
            # Close current dialog
            if self._goals_dlg:
                self._goals_dlg.open = False
                self.page.update()
            # Reopen with fresh data from API
            await self._open_monthly_goals()
        except Exception as e:
            print(f"Error al guardar objetivo: {e}")

    async def _edit_existing_goal(self, goal: dict) -> None:
        """Open a sub-dialog to edit an existing goal."""
        # Close main goals dialog first
        if self._goals_dlg:
            self._goals_dlg.open = False
            self.page.update()

        goal_text_f = ft.TextField(
            label="Objetivo",
            value=goal.get("goal_text", ""),
            multiline=True,
            min_lines=2,
            max_lines=4,
        )
        action_f = ft.TextField(
            label="Plan de accion",
            value=goal.get("action_plan", ""),
            multiline=True,
            min_lines=2,
            max_lines=4,
        )

        async def _save_edit(_: ft.ControlEvent) -> None:
            edit_dlg.open = False
            self.page.update()
            data = {
                "goal_text": goal_text_f.value or "",
                "action_plan": action_f.value or "",
                "is_completed": goal.get("is_completed", False),
            }
            try:
                await update_monthly_goal(
                    app_state.workspace_id, goal["id"], data
                )
            except Exception as ex:
                print(f"Error saving goal: {ex}")
            await self._open_monthly_goals()

        async def _cancel_edit(_: ft.ControlEvent) -> None:
            edit_dlg.open = False
            self.page.update()
            await self._open_monthly_goals()

        edit_dlg = ft.AlertDialog(
            title=ft.Text(
                f"Editar: {calendar.month_name[goal['month']]} {goal['year']}"),
            content=ft.Container(
                content=ft.Column([goal_text_f, action_f], spacing=10),
                padding=ft.Padding(top=10, bottom=10, left=10, right=10),
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=_cancel_edit),
                ft.Button("Guardar", on_click=_save_edit),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            modal=True,
        )
        edit_dlg.open = True
        self.page.overlay.append(edit_dlg)
        self.page.update()

    async def _delete_existing_goal(self, goal: dict) -> None:
        """Confirm and delete a goal."""
        # Close main goals dialog first
        if self._goals_dlg:
            self._goals_dlg.open = False
            self.page.update()

        async def _confirm(_: ft.ControlEvent) -> None:
            confirm_dlg.open = False
            self.page.update()
            try:
                await delete_goal_api(
                    app_state.workspace_id, goal["id"]
                )
            except Exception as ex:
                print(f"Error deleting goal: {ex}")
            await self._open_monthly_goals()

        async def _cancel_delete(_: ft.ControlEvent) -> None:
            confirm_dlg.open = False
            self.page.update()
            await self._open_monthly_goals()

        confirm_dlg = ft.AlertDialog(
            title=ft.Text("Eliminar objetivo"),
            content=ft.Text(
                f"¿Eliminar objetivo de "
                f"{calendar.month_name[goal['month']]} {goal['year']}?"
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=_cancel_delete),
                ft.Button("Eliminar", on_click=_confirm),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            modal=True,
        )
        confirm_dlg.open = True
        self.page.overlay.append(confirm_dlg)
        self.page.update()

    def _close_goals_dialog(self, e: ft.ControlEvent) -> None:
        """Close all AlertDialogs (main + any lingering sub-dialogs)."""
        for c in self.page.overlay:
            if isinstance(c, ft.AlertDialog):
                c.open = False
        self.page.update()
