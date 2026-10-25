"""The app settings loader (``fno/shared/config.py``): allowed keys load, unknown keys are refused, overrides merge."""

from __future__ import annotations

from pathlib import Path

import pytest

from fno.shared.config import ALLOWED_APP_KEYS, ConfigError, load_app_config, load_config


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_allowed_keys_load(tmp_path: Path) -> None:
    cfg = load_app_config(_write(tmp_path, "provider: sample\nquotes:\n  provider: auto\n"))
    assert cfg["provider"] == "sample"
    assert cfg["quotes"] == {"provider": "auto"}


def test_unknown_key_is_rejected(tmp_path: Path) -> None:
    path = _write(tmp_path, "provider: sample\nmystery_setting: 1\n")
    with pytest.raises(ConfigError) as caught:
        load_app_config(path)
    assert "mystery_setting" in str(caught.value)


def test_overrides_merge_over_file(tmp_path: Path) -> None:
    path = _write(tmp_path, "provider: nse\nlot_sizes:\n  NIFTY: 75\n")
    cfg = load_app_config(path, {"provider": "groww", "lot_sizes": {"BANKNIFTY": 35}})
    assert cfg["provider"] == "groww"
    assert cfg["lot_sizes"] == {"NIFTY": 75, "BANKNIFTY": 35}  # nested dicts deep-merge


def test_load_config_does_not_check_keys(tmp_path: Path) -> None:
    """``load_config`` (used by frozen research inputs) accepts any key, unlike ``load_app_config``."""
    path = _write(tmp_path, "legacy_only_key: 1\n")
    assert load_config(path) == {"legacy_only_key": 1}


def test_empty_file_is_empty_mapping(tmp_path: Path) -> None:
    assert load_app_config(_write(tmp_path, "")) == {}


def test_every_allowed_key_is_a_string() -> None:
    assert all(isinstance(key, str) for key in ALLOWED_APP_KEYS)
