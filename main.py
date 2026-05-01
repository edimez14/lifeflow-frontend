from __future__ import annotations

import flet as ft

from screens.calendar_screen import CalendarScreen
from screens.timer_widget import TimerWidget
from screens.workspace_selector import WorkspaceSelectorScreen
from state import ws_client
from state.app_state import app_state

_timer_widget: TimerWidget | None = None


def _wire_timer_refs(timer: TimerWidget, page: ft.Page) -> None:
    """Pass direct control references to the WS client for lean tick updates."""

    ws_client.set_timer_refs(
        label=timer._display._label,
        state_text=timer._display._state_text,
        pause_btn=timer._pause_btn,
        resume_btn=timer._resume_btn,
        cancel_btn=timer._cancel_btn,
        start_btn=timer._start_without_task_btn,
        page=page,
    )


def render_app(page: ft.Page) -> None:
    """Render the current app screen."""

    page.controls.clear()

    if app_state.workspace_id:
        # Workspace is active, show calendar as main view with timer panel
        calendar_screen = CalendarScreen(page)
        timer_panel = _get_timer_widget(page)

        main_content = ft.Row(
            controls=[
                ft.Column(
                    controls=[calendar_screen.view],
                    expand=True,
                ),
                ft.VerticalDivider(width=1),
                ft.Column(
                    controls=[timer_panel],
                    width=240,
                    alignment=ft.MainAxisAlignment.START,
                ),
            ],
            expand=True,
            spacing=0,
        )
        page.add(main_content)
        page.run_task(calendar_screen._load_data)
    elif app_state.current_screen == "workspace_selector":
        selector_screen = WorkspaceSelectorScreen(
            page, on_authenticated=lambda: render_app(page))
        page.add(selector_screen.build())
        page.run_task(selector_screen.load_workspaces)
    else:
        app_state.set_screen("workspace_selector")
        render_app(page)

    page.update()


def _get_timer_widget(page: ft.Page) -> TimerWidget:
    """Return the singleton timer widget instance."""

    global _timer_widget
    if _timer_widget is None:
        _timer_widget = TimerWidget()
        _wire_timer_refs(_timer_widget, page)
    return _timer_widget


def main_view(page: ft.Page) -> None:
    """Render the app entrypoint for Lifeflow frontend."""

    page.title = "Lifeflow"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    app_state.bind_page(page)
    # Start WebSocket client globally so tick/finished handlers are active.
    ws_client.start()
    app_state.set_screen("workspace_selector")
    render_app(page)


if __name__ == "__main__":
    ft.run(main_view)
