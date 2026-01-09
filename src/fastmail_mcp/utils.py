"""Utility helpers for environment handling and logging setup."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

_ENV_COMMENT_PREFIXES = ("#", "//")


def load_env(path: Path | None = None) -> Dict[str, str]:
    """Load key/value pairs from a .env file without overriding existing vars."""

    env_path = path or Path(".env")
    if env_path.exists():
        for raw_line in env_path.read_text().splitlines():
            line = raw_line.strip()
            if not line or line.startswith(_ENV_COMMENT_PREFIXES):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())
    return {key: os.environ[key] for key in os.environ.keys()}


def get_required_env(key: str) -> str:
    """Return a required environment variable or raise a helpful error."""

    try:
        value = os.environ[key]
    except KeyError as exc:  # pragma: no cover - defensive branch
        raise RuntimeError(f"Missing required environment variable: {key}") from exc
    if not value:
        raise RuntimeError(f"Environment variable {key} is empty")
    return value
