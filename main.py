from __future__ import annotations

import flet as ft


def main_view(page: ft.Page) -> None:
    """Render the initial loading screen for Lifeflow."""

    page.title = "Lifeflow"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.add(
        ft.Text(
            "Lifeflow cargando...",
            size=24,
            weight=ft.FontWeight.BOLD,
        )
    )


if __name__ == "__main__":
    ft.app(target=main_view)
