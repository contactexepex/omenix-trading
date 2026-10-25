"""Loads secrets from a private KEY=VALUE file (default ~/.trading.env) on every platform.

Values already set in the environment win, so cloud settings and service managers keep control.
The file is never part of the repository.
"""

from __future__ import annotations

import os
from pathlib import Path

ENV_FILE_NAME = ".trading.env"
COMMENT_PREFIX = "#"


def parse_env_lines(lines: list[str]) -> dict[str, str]:
    values = {}
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith(COMMENT_PREFIX) or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.split(f" {COMMENT_PREFIX}", 1)[0].strip().strip('"').strip("'")
        if key.strip() and value:
            values[key.strip()] = value
    return values


def load_env_file(path: Path | None = None) -> list[str]:
    """Set variables from the file that are not already set. Returns the names that were loaded."""
    path = path or Path.home() / ENV_FILE_NAME
    if not path.is_file():
        return []
    loaded = []
    for key, value in parse_env_lines(path.read_text(encoding="utf-8").splitlines()).items():
        if key not in os.environ:
            os.environ[key] = value
            loaded.append(key)
    return loaded
