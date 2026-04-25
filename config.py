from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def _read_dotenv_file() -> dict[str, str]:
    """Read key/value pairs from the frontend .env file."""

    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")

    return values


def get_env_value(key: str) -> str | None:
    """Return an environment value from OS vars or frontend .env."""

    system_value = os.getenv(key)
    if system_value:
        return system_value

    return _read_dotenv_file().get(key)


BACKEND_URL = get_env_value("BACKEND_URL")
if not BACKEND_URL:
    raise RuntimeError("BACKEND_URL is required")
