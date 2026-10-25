"""The risk manager's settings: the `risk` block of `config.yaml` (story C2), read once and checked, never hard-coded.

Every limit, scenario and margin setting must be present and valid; a missing or malformed one is an error at start-up,
so no proposal is ever checked against a default the owner did not set.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..constants import STRESSED_MARGIN_METHODS, STRESSED_MARGIN_MULTIPLIER


class RiskSettingsError(ValueError):
    """The `risk` block is missing a setting, or a setting is not usable."""


@dataclass(frozen=True)
class Scenario:
    """One stress scenario: NIFTY moves by `nifty_move_pct`, every leg's implied volatility is multiplied by
    `iv_factor`, and `days` calendar days pass."""

    name: str
    nifty_move_pct: float
    iv_factor: float
    days: int = 1


@dataclass(frozen=True)
class ExposureSettings:
    """Design 8.1: account loss from a NIFTY move of `nifty_move_pct` (either way) and from a rise of `iv_rise_points`
    volatility points, each at most its limit."""

    nifty_move_pct: float
    max_move_loss_rs: float
    iv_rise_points: float
    max_iv_loss_rs: float


@dataclass(frozen=True)
class StressedMarginSettings:
    """The one frozen stressed-margin method. `multiplier` reads its factor from `factor_file`, A14c's append-only
    file (story C2d; a row expires after `max_age_days`); `scenario_lookup` reads a margin per scenario from
    `scenario_file`."""

    method: str
    factor_file: Path | None
    max_age_days: int
    scenario_file: Path | None


@dataclass(frozen=True)
class RiskSettings:
    """What every risk profile shares; each profile's limits are in `profile_settings.py` (story C5)."""

    scenarios: tuple[Scenario, ...]  # C2's stress scenarios (the profiles that run `stress_loss`)
    stress_line: tuple[Scenario, ...]  # design 6.2's daily stress line, a report (story C5)
    margins_file: Path
    stressed_margin: StressedMarginSettings


def get_setting(block: Mapping[str, Any], key: str, where: str) -> Any:
    if not isinstance(block, Mapping) or key not in block or block[key] is None:
        raise RiskSettingsError(f"config.yaml risk{where}: `{key}` is required")
    return block[key]


def positive_setting(block: Mapping[str, Any], key: str, where: str = "") -> float:
    value = get_setting(block, key, where)
    if isinstance(value, bool) or not isinstance(value, int | float) or value <= 0:
        raise RiskSettingsError(f"config.yaml risk{where}: `{key}` must be a positive number, not {value!r}")
    return float(value)


def count_setting(block: Mapping[str, Any], key: str, where: str = "") -> int:
    value = positive_setting(block, key, where)
    if value != int(value):
        raise RiskSettingsError(f"config.yaml risk{where}: `{key}` must be a whole number, not {value!r}")
    return int(value)


def _scenario(row: Mapping[str, Any]) -> Scenario:
    move = get_setting(row, "nifty_move_pct", ".scenarios")
    if isinstance(move, bool) or not isinstance(move, int | float) or move <= -100:
        raise RiskSettingsError(f"config.yaml risk.scenarios: bad nifty_move_pct {move!r}")
    return Scenario(
        str(get_setting(row, "name", ".scenarios")),
        float(move),
        positive_setting(row, "iv_factor", ".scenarios"),
        count_setting(row, "days", ".scenarios"),
    )


def scenarios_at(block: Mapping[str, Any], key: str = "scenarios") -> tuple[Scenario, ...]:
    """A non-empty list of uniquely named scenarios under `key` (C2's limit scenarios, C5's stress line)."""
    rows = get_setting(block, key, "")
    if not isinstance(rows, list) or not rows:
        raise RiskSettingsError(f"config.yaml risk: `{key}` must be a non-empty list")
    scenarios = tuple(_scenario(row) for row in rows)
    names = [s.name for s in scenarios]
    if len(set(names)) != len(names):
        raise RiskSettingsError(f"config.yaml risk.{key}: names must be unique: {names}")
    return scenarios


def exposure_at(block: Mapping[str, Any], where: str) -> ExposureSettings:
    exposure, inner = get_setting(block, "exposure", where), f"{where}.exposure"
    keys = ("nifty_move_pct", "max_move_loss_rs", "iv_rise_points", "max_iv_loss_rs")
    return ExposureSettings(*(positive_setting(exposure, k, inner) for k in keys))


FACTOR_MOVED_TO_FILE = frozenset({"multiplier", "source", "as_of"})
FACTOR_IN_FILE = "not allowed: the factor is read from factor_file, A14c's file (story C2d)"


def _stressed_margin(block: Mapping[str, Any], root: Path) -> StressedMarginSettings:
    """Only the method and its expiry are required here: a missing factor file or row fails closed when a proposal
    is checked (MarginRoom), so the desk refuses trades instead of refusing to start. The factor itself is never in
    config (story C2d): `multiplier`, `source` or `as_of` here is refused, so two sources can never disagree."""
    stressed = get_setting(block, "stressed_margin", "")
    method = get_setting(stressed, "method", ".stressed_margin")
    if method not in STRESSED_MARGIN_METHODS:
        raise RiskSettingsError(f"config.yaml risk.stressed_margin: method must be one of {STRESSED_MARGIN_METHODS}")
    moved = sorted(FACTOR_MOVED_TO_FILE & set(stressed))
    if moved:
        raise RiskSettingsError(f"config.yaml risk.stressed_margin: {', '.join(moved)} {FACTOR_IN_FILE}")
    factor_file, scenario_file = stressed.get("factor_file"), stressed.get("scenario_file")
    return StressedMarginSettings(
        method,
        root / factor_file if factor_file else None,
        count_setting(stressed, "max_age_days", ".stressed_margin"),
        root / scenario_file if scenario_file else None,
    )


RISK_KEYS = frozenset({"profiles", "scenarios", "stress_line", "margins", "stressed_margin"})


def risk_settings(config: Mapping[str, Any], root: Path) -> RiskSettings:
    """The checked `risk` block of an app config (`fno.config.load_app_config`); file paths are relative to `root`.
    A key outside `RISK_KEYS` (say a leftover flat `max_open_trades`, judge 105) is an error: it would look like a
    limit while nothing runs it."""
    block = get_setting(config, "risk", "")
    stray = sorted(set(block) - RISK_KEYS) if isinstance(block, Mapping) else []
    if stray:
        raise RiskSettingsError(f"config.yaml risk: {stray} are not settings; limits belong under risk.profiles")
    margins = get_setting(block, "margins", "")
    settings = RiskSettings(
        scenarios_at(block),
        scenarios_at(block, "stress_line"),
        root / str(get_setting(margins, "file", ".margins")),
        _stressed_margin(block, root),
    )
    if settings.stressed_margin.method == STRESSED_MARGIN_MULTIPLIER and settings.stressed_margin.scenario_file:
        raise RiskSettingsError("config.yaml risk.stressed_margin: scenario_file belongs to scenario_lookup only")
    return settings
