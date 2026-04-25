from __future__ import annotations

import flet as ft

from screens.workspace_selector import WorkspaceSelectorScreen
from state.app_state import app_state


def render_app(page: ft.Page) -> None:
    """Render the current app screen."""

    page.controls.clear()

    if app_state.current_screen == "workspace_home":
        workspace_name = app_state.user_data.get("workspace_name", "")
        page.add(
            ft.Column(
                controls=[
                    ft.Text("Workspace activo / Active workspace", size=16),
                    ft.Text(workspace_name, size=24,
                            weight=ft.FontWeight.BOLD),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            )
        )
    else:
        selector_screen = WorkspaceSelectorScreen(
            page, on_authenticated=lambda: render_app(page))
        page.add(selector_screen.build())
        page.run_task(selector_screen.load_workspaces)

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
