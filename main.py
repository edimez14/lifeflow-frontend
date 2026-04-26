from __future__ import annotations

import flet as ft

from screens.calendar_screen import CalendarScreen
from screens.workspace_selector import WorkspaceSelectorScreen
from state.app_state import app_state


def render_app(page: ft.Page) -> None:
    """Render the current app screen."""

    page.controls.clear()

    if app_state.workspace_id:
        # Workspace is active, show calendar as main view
        calendar_screen = CalendarScreen(page)
        page.add(calendar_screen.view)
        page.run_task(calendar_screen._load_data)  # initial load
    elif app_state.current_screen == "workspace_selector":
        selector_screen = WorkspaceSelectorScreen(
            page, on_authenticated=lambda: render_app(page))
        page.add(selector_screen.build())
        page.run_task(selector_screen.load_workspaces)
    else:
        # Fallback: show workspace selector
        app_state.set_screen("workspace_selector")
        render_app(page)

    page.update()


def main_view(page: ft.Page) -> None:
    """Render the app entrypoint for Lifeflow frontend."""

    page.title = "Lifeflow"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    app_state.bind_page(page)
    app_state.set_screen("workspace_selector")
    render_app(page)


if __name__ == "__main__":
    ft.run(main_view)
