"""Settings: the app's `config.yaml` (checked against the allowed keys) and plain reading of frozen research inputs."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

# Repository root: config.py sits at fno/shared/config.py, so the root is three levels up (where config.yaml lives).
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = ROOT / "config.yaml"

# Top-level keys the ingestion app's config.yaml may hold. A story that adds a setting adds its key here, with a test.
ALLOWED_APP_KEYS = frozenset(
    {
        "provider",
        "promotion",
        "quotes",
        "lot_sizes",
        "slack",
    }  # fmt: skip
)


class ConfigError(ValueError):
    """The app's settings file holds a key the app does not use (often one left from the removed old desk)."""


def _merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def load_config(path: str | Path | None = None, overrides: dict[str, Any] | None = None) -> dict:
    """A settings file as written, then any explicit overrides. No key check: research studies use this to read their
    own frozen input copies, which keep the keys of their time."""
    path = Path(path) if path else DEFAULT_CONFIG_PATH
    with open(path, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}
    return _merge(cfg, overrides or {})


def load_app_config(path: str | Path | None = None, overrides: dict[str, Any] | None = None) -> dict:
    """The app's settings: like `load_config`, but any top-level key outside `ALLOWED_APP_KEYS` is an error, so a
    stale or misspelt setting is never silently ignored."""
    cfg = load_config(path, overrides)
    unknown = sorted(set(cfg) - ALLOWED_APP_KEYS)
    if unknown:
        raise ConfigError(
            f"Unknown setting(s) in config.yaml: {', '.join(unknown)}. Allowed: {sorted(ALLOWED_APP_KEYS)}"
        )
    return cfg
