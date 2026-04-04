from __future__ import annotations

import os
from typing import Any

import httpx

BACKEND_URL = os.getenv("BACKEND_URL")
if not BACKEND_URL:
    raise RuntimeError("BACKEND_URL is required")
DEFAULT_TIMEOUT = 30.0

_client: httpx.AsyncClient | None = None
_workspace_token: str | None = None


def set_workspace_token(token: str | None) -> None:
    """Set the active workspace token used on API requests."""

    global _workspace_token
    _workspace_token = token


def get_workspace_token() -> str | None:
    """Return the active workspace token."""

    return _workspace_token


def get_client() -> httpx.AsyncClient:
    """Return a singleton async HTTP client."""

    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            base_url=BACKEND_URL,
            timeout=DEFAULT_TIMEOUT,
            headers={"Content-Type": "application/json"},
        )
    return _client


async def close_client() -> None:
    """Close the shared HTTP client if it was created."""

    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def _build_headers(headers: dict[str, str] | None = None) -> dict[str, str]:
    """Build request headers and attach the workspace token when available."""

    merged_headers: dict[str, str] = {}
    if headers:
        merged_headers.update(headers)

    if _workspace_token:
        merged_headers["Authorization"] = f"Bearer {_workspace_token}"

    return merged_headers


async def request(
    method: str,
    url: str,
    **kwargs: Any,
) -> httpx.Response:
    """Send an HTTP request using the shared client."""

    client = get_client()
    headers = _build_headers(kwargs.pop("headers", None))
    return await client.request(method, url, headers=headers, **kwargs)


async def get(url: str, **kwargs: Any) -> httpx.Response:
    """Send a GET request."""

    return await request("GET", url, **kwargs)


async def post(url: str, **kwargs: Any) -> httpx.Response:
    """Send a POST request."""

    return await request("POST", url, **kwargs)


async def put(url: str, **kwargs: Any) -> httpx.Response:
    """Send a PUT request."""

    return await request("PUT", url, **kwargs)


async def delete(url: str, **kwargs: Any) -> httpx.Response:
    """Send a DELETE request."""

    return await request("DELETE", url, **kwargs)
