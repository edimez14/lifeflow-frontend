from __future__ import annotations

import flet as ft

from components.sidebar import Sidebar
from screens.calendar_screen import CalendarScreen
from screens.tasks_screen import TasksScreen
from screens.timer_widget import TimerWidget
from screens.workspace_selector import WorkspaceSelectorScreen
from state import ws_client
from state.app_state import app_state

_timer_widget: TimerWidget | None = None
_active_screen_name: str | None = None
_active_screen_obj: object | None = None


def _wire_timer_refs(timer: TimerWidget, page: ft.Page) -> None:
    """Pass direct control references to the WS client for lean tick updates."""

    ws_client.set_timer_refs(
        label=timer._display._label,
        state_text=timer._display._state_text,
        pause_btn=timer._pause_btn,
        resume_btn=timer._resume_btn,
        cancel_btn=timer._cancel_btn,
        start_btn=timer._play_btn,
        page=page,
    )


def render_app(page: ft.Page) -> None:
    """Render the current app screen."""

    page.controls.clear()

    if app_state.workspace_id:
        main_screen = _get_main_screen(page)
        timer_panel = _get_timer_widget(page)

        sidebar = Sidebar(
            on_navigate=_on_navigate,
            on_back=_on_back,
        )

        header = ft.Row(
            controls=[
                ft.IconButton(
                    icon=ft.Icons.MENU,
                    tooltip="Toggle sidebar",
                    on_click=_on_toggle_sidebar,
                ),
                ft.IconButton(
                    icon=ft.Icons.TIMER,
                    tooltip="Toggle timer",
                    on_click=_on_toggle_timer,
                ),
            ],
            spacing=8,
        )

        content_row_controls: list[ft.Control] = []
        if app_state.show_sidebar:
            content_row_controls.extend([
                sidebar,
                ft.VerticalDivider(width=1),
            ])

        content_row_controls.append(
            ft.Container(content=main_screen, expand=True)
        )

        if app_state.show_timer:
            content_row_controls.extend([
                ft.VerticalDivider(width=1),
                ft.Column(
                    controls=[timer_panel],
                    width=240,
                    alignment=ft.MainAxisAlignment.START,
                ),
            ])

        main_content = ft.Column(
            controls=[
                header,
                ft.Row(
                    controls=content_row_controls,
                    expand=True,
                    spacing=0,
                ),
            ],
            expand=True,
            spacing=8,
        )
        page.add(main_content)
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


def _get_main_screen(page: ft.Page) -> ft.Control:
    """Return the active screen based on the current navigation state."""

    global _active_screen_name, _active_screen_obj

    screen_name = app_state.current_screen
    if screen_name in ("workspace_home", "calendar"):
        screen_name = "calendar"
    elif screen_name not in ("calendar", "tasks"):
        screen_name = "calendar"

    if _active_screen_name != screen_name:
        if _active_screen_obj is not None and hasattr(_active_screen_obj, "dispose"):
            _active_screen_obj.dispose()

        if screen_name == "tasks":
            _active_screen_obj = TasksScreen(page)
        else:
            _active_screen_obj = CalendarScreen(page)
            page.run_task(_active_screen_obj._load_data)

        _active_screen_name = screen_name

    return _active_screen_obj.view


def _on_navigate(screen_name: str) -> None:
    """Handle navigation from the sidebar."""
    app_state.set_screen(screen_name)
    if app_state.page is not None:
        render_app(app_state.page)


def _on_back() -> None:
    """Return to workspace selector."""
    app_state.clear_workspace()
    app_state.set_screen("workspace_selector")
    if app_state.page is not None:
        render_app(app_state.page)


def _on_toggle_sidebar(_: ft.ControlEvent) -> None:
    """Toggle the sidebar visibility."""

    app_state.toggle_sidebar()
    if app_state.page is not None:
        render_app(app_state.page)


def _on_toggle_timer(_: ft.ControlEvent) -> None:
    """Toggle the timer panel visibility."""

    app_state.toggle_timer()
    if app_state.page is not None:
        render_app(app_state.page)


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
