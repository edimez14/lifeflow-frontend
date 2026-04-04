from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from flet import Page

from state import http_client, ws_client


@dataclass
class AppState:
    """Global application state shared across screens."""

    page: Page | None = None
    current_screen: str = "loading"
    workspace_id: str | None = None
    workspace_token: str | None = None
    user_data: dict[str, Any] = field(default_factory=dict)

    def bind_page(self, page: Page) -> None:
        """Bind the Flet page used by the app."""

        self.page = page

    def set_screen(self, screen_name: str) -> None:
        """Update the current screen name."""

        self.current_screen = screen_name
        self.refresh()

    def set_workspace(self, workspace_id: str | None, token: str | None = None) -> None:
        """Update the active workspace and sync HTTP/WS clients."""

        self.workspace_id = workspace_id
        self.workspace_token = token
        http_client.set_workspace_token(token)
        ws_client.set_workspace_id(workspace_id)
        self.refresh()

    def set_user_data(self, data: dict[str, Any]) -> None:
        """Store shared user data for the whole app."""

        self.user_data = data
        self.refresh()

    def clear_workspace(self) -> None:
        """Clear the active workspace information."""

        self.set_workspace(None, None)

    def refresh(self) -> None:
        """Refresh the current page if it is available."""

        if self.page is not None:
            self.page.update()


app_state = AppState()
