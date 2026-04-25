from __future__ import annotations

import flet as ft
import httpx
from collections.abc import Callable

from api.workspaces_api import auth_workspace, list_workspaces
from state.app_state import app_state


class WorkspaceSelectorScreen:
    """Render and manage the workspace selector screen."""

    def __init__(self, page: ft.Page, on_authenticated: Callable[[], None]) -> None:
        self.page = page
        self.on_authenticated = on_authenticated
        self.workspaces: list[dict] = []
        self.selected_workspace_id: str | None = None
        self.selected_workspace_name: str | None = None

        self.title = ft.Text(
            "Selecciona tu workspace / Select your workspace",
            size=24,
            weight=ft.FontWeight.BOLD,
            text_align=ft.TextAlign.CENTER,
        )
        self.subtitle = ft.Text(
            "Elige un espacio para continuar / Choose a workspace to continue",
            size=14,
            text_align=ft.TextAlign.CENTER,
        )
        self.status_text = ft.Text("", color=ft.Colors.RED_500)
        self.loading_text = ft.Text("Cargando... / Loading...", visible=False)
        self.workspace_grid = ft.ResponsiveRow([], spacing=12, run_spacing=12)

        self.password_field = ft.TextField(
            label="Contraseña / Password",
            password=True,
            can_reveal_password=True,
            width=320,
        )
        self.password_error = ft.Text("", color=ft.Colors.RED_500)
        self.private_auth_loading = ft.Row(
            controls=[
                ft.ProgressRing(width=16, height=16, stroke_width=2),
                ft.Text("Validando... / Validating...", size=12),
            ],
            spacing=8,
            visible=False,
        )
        self.auth_button = ft.Button(
            content=ft.Text("Entrar / Enter"),
            on_click=self.on_private_auth,
        )
        self.cancel_button = ft.Button(
            content=ft.Text("Cancelar / Cancel"),
            on_click=self.on_cancel_private,
        )

        self.private_auth_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Workspace privado / Private workspace"),
            content=ft.Column(
                controls=[
                    self.password_field,
                    self.password_error,
                    self.private_auth_loading,
                ],
                spacing=8,
                tight=True,
            ),
            actions=[self.cancel_button, self.auth_button],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def build(self) -> ft.Control:
        """Build screen controls."""

        return ft.Container(
            expand=True,
            content=ft.Column(
                controls=[
                    self.title,
                    self.subtitle,
                    self.loading_text,
                    self.status_text,
                    self.workspace_grid,
                ],
                width=900,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=16,
            ),
            padding=20,
        )

    async def load_workspaces(self) -> None:
        """Load workspaces from backend."""

        self.loading_text.visible = True
        self.status_text.value = ""
        self.page.update()

        try:
            self.workspaces = await list_workspaces()
            self.render_workspaces()
        except httpx.HTTPError:
            self.status_text.value = "No se pudo cargar la lista / Could not load workspace list"
        finally:
            self.loading_text.visible = False
            self.page.update()

    def render_workspaces(self) -> None:
        """Render workspace cards in the selector."""

        cards: list[ft.Control] = []
        for workspace in self.workspaces:
            workspace_id = str(workspace.get("id", ""))
            name = str(workspace.get("name", ""))
            workspace_type = str(workspace.get("workspace_type", "public"))
            color = str(workspace.get("color", "#DDDDDD"))
            icon_name = str(workspace.get("icon", "folder"))

            cards.append(
                ft.Container(
                    col={"sm": 12, "md": 6, "lg": 4},
                    content=ft.Card(
                        content=ft.Container(
                            padding=14,
                            content=ft.Column(
                                controls=[
                                    ft.Row(
                                        controls=[
                                            ft.Icon(name=icon_name,
                                                    color=color, size=28),
                                            ft.Text(
                                                name, weight=ft.FontWeight.BOLD, size=18),
                                        ],
                                        spacing=10,
                                    ),
                                    ft.Text(
                                        "Público / Public"
                                        if workspace_type == "public"
                                        else "Privado / Private",
                                        color=ft.Colors.GREY_700,
                                    ),
                                    ft.Button(
                                        content=ft.Text("Entrar / Enter"),
                                        on_click=lambda e, wid=workspace_id, wname=name, wtype=workspace_type: self.on_select_workspace(
                                            wid, wname, wtype),
                                    ),
                                ],
                                spacing=10,
                            ),
                        )
                    ),
                )
            )

        self.workspace_grid.controls = cards
        self.page.update()

    def on_select_workspace(self, workspace_id: str, workspace_name: str, workspace_type: str) -> None:
        """Handle workspace selection."""

        self.selected_workspace_id = workspace_id
        self.selected_workspace_name = workspace_name
        self.status_text.value = ""

        if workspace_type == "private":
            self.password_field.value = ""
            self.password_error.value = ""
            self.private_auth_loading.visible = False
            self.auth_button.disabled = False
            self.page.dialog = self.private_auth_dialog
            self.private_auth_dialog.open = True
            self.page.update()
            return

        self.page.run_task(self.authenticate_workspace,
                           workspace_id, workspace_name, None)

    def on_private_auth(self, _: ft.ControlEvent) -> None:
        """Handle private workspace password submit."""

        if not self.selected_workspace_id or not self.selected_workspace_name:
            return
        self.page.run_task(
            self.authenticate_workspace,
            self.selected_workspace_id,
            self.selected_workspace_name,
            self.password_field.value,
        )

    def on_cancel_private(self, _: ft.ControlEvent) -> None:
        """Hide private workspace auth block."""

        self.private_auth_dialog.open = False
        self.password_error.value = ""
        self.private_auth_loading.visible = False
        self.auth_button.disabled = False
        self.page.update()

    async def authenticate_workspace(
        self,
        workspace_id: str,
        workspace_name: str,
        password: str | None,
    ) -> None:
        """Authenticate workspace and update global state."""

        is_private_auth = password is not None

        if is_private_auth:
            self.password_error.value = ""
            self.private_auth_loading.visible = True
            self.auth_button.disabled = True
        else:
            self.status_text.value = "Validando... / Validating..."
        self.page.update()

        try:
            token = await auth_workspace(workspace_id, password=password)
            app_state.set_workspace(workspace_id, token)
            app_state.set_user_data({"workspace_name": workspace_name})
            app_state.set_screen("workspace_home")
            self.private_auth_dialog.open = False
            self.on_authenticated()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                self.password_error.value = "Contraseña incorrecta / Invalid password"
            else:
                self.status_text.value = "Error de autenticación / Authentication error"
            self.page.update()
        except httpx.HTTPError:
            self.status_text.value = "No se pudo conectar / Could not connect"
            self.page.update()
        finally:
            self.private_auth_loading.visible = False
            self.auth_button.disabled = False
            self.page.update()
