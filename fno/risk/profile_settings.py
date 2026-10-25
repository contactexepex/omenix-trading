"""One risk profile's settings (stories C2 and C5): `config.yaml` `risk.profiles.<name>`, read once and checked.

A profile names the rules it runs (`rules`) and holds exactly the settings those rules need, so a rule is never on or
off by a missing key: an unknown rule, a missing setting, or a setting no listed rule uses is an error at start-up. Four
rules run in every profile (the account size, the per-trade loss, the drawdown brake and the margin room).

Owner decisions (`docs/DESK_DECISIONS.md`): the books run on Rs 20 lakh with Rs 10,000 a trade (14 Oct 2026), a
Rs 30,000 bucket cap, a Rs 1.5 lakh open-risk cap, Rs 50,000 of new risk a session and a Rs 1.2 lakh brake, and drop
the flat 3 open trades and C2's old stress and exposure limits (15 Oct 2026, "1 A", "2 A"). The Manual paper account
keeps its 13 Oct 2026 limits.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ..constants import BUCKET_SIDES
from .settings import ExposureSettings, RiskSettingsError, count_setting, exposure_at, get_setting, positive_setting

AGE_DAYS, AGE_SESSIONS = "margin_max_age_days", "margin_max_age_sessions"
RULE_SETTINGS = {
    "paper_account": ("paper_account_rs",),
    "max_loss_per_trade": ("max_loss_per_trade_rs",),
    "drawdown_brake": ("drawdown_brake_rs",),
    "margin_room": (),
    "max_open_trades": ("max_open_trades",),
    "stress_loss": ("max_stress_loss_rs",),
    "exposure_limit": ("exposure",),
    "bucket_cap": ("bucket_cap_rs", "bucket_sides"),
    "open_risk_cap": ("open_risk_cap_rs", "bucket_sides"),
    "new_risk_per_day": ("new_risk_per_day_rs", "bucket_sides"),
}
EVERY_PROFILE = ("paper_account", "max_loss_per_trade", "drawdown_brake", "margin_room")


@dataclass(frozen=True)
class ProfileSettings:
    name: str
    rules: tuple[str, ...]  # the rules this profile runs, in config order
    paper_account_rs: float  # every account of the profile opens with this cash (E1)
    max_loss_per_trade_rs: float
    drawdown_brake_rs: float
    margin_age_days: int | None  # exactly one of the two margin ages is set
    margin_age_sessions: int | None
    max_open_trades: int | None = None
    max_stress_loss_rs: float | None = None
    exposure: ExposureSettings | None = None
    bucket_cap_rs: float | None = None
    open_risk_cap_rs: float | None = None
    new_risk_per_day_rs: float | None = None
    bucket_sides: Mapping[str, tuple[str, ...]] | None = None  # structure code -> its sides; unlisted codes refused


def _where(name: str) -> str:
    return f".profiles.{name}"


def _rules(block: Mapping[str, Any], where: str) -> tuple[str, ...]:
    rules = get_setting(block, "rules", where)
    if not isinstance(rules, list) or len(set(rules)) != len(rules):
        raise RiskSettingsError(f"config.yaml risk{where}: `rules` must be a list of distinct rule names")
    unknown = [r for r in rules if r not in RULE_SETTINGS]
    missing = [r for r in EVERY_PROFILE if r not in rules]
    if unknown or missing:
        raise RiskSettingsError(f"config.yaml risk{where}.rules: unknown {unknown}, required but missing {missing}")
    return tuple(rules)


def _check_keys(block: Mapping[str, Any], rules: tuple[str, ...], where: str) -> None:
    used = {"rules", AGE_DAYS, AGE_SESSIONS} | {key for rule in rules for key in RULE_SETTINGS[rule]}
    unused = sorted(set(block) - used)
    if unused:
        raise RiskSettingsError(f"config.yaml risk{where}: {unused} belong to no rule this profile runs")
    if (AGE_DAYS in block) == (AGE_SESSIONS in block):
        raise RiskSettingsError(f"config.yaml risk{where}: set exactly one of `{AGE_DAYS}` and `{AGE_SESSIONS}`")


def _as_sides(value: Any) -> tuple:
    if isinstance(value, str):
        return (value,)
    return tuple(value) if isinstance(value, list) else ()


def _sides(block: Mapping[str, Any], where: str) -> dict[str, tuple[str, ...]]:
    """Structure code -> its sides: one side, or a list (a directional spread: its direction and a volatility side)."""
    sides = get_setting(block, "bucket_sides", where)
    if not isinstance(sides, Mapping) or not sides:
        raise RiskSettingsError(f"config.yaml risk{where}: `bucket_sides` must map structure codes to sides")
    listed = {str(code): _as_sides(side) for code, side in sides.items()}
    wrong = {c: s for c, s in listed.items() if not s or len(set(s)) != len(s) or set(s) - set(BUCKET_SIDES)}
    if wrong:
        raise RiskSettingsError(
            f"config.yaml risk{where}.bucket_sides: each code needs distinct sides from {BUCKET_SIDES}: {wrong}"
        )
    return listed


def _optional(block: Mapping[str, Any], rules: tuple[str, ...], where: str) -> dict[str, Any]:
    """The settings of the profile's optional rules, each read and checked only when its rule runs."""
    readers = {
        "max_open_trades": lambda: {"max_open_trades": count_setting(block, "max_open_trades", where)},
        "stress_loss": lambda: {"max_stress_loss_rs": positive_setting(block, "max_stress_loss_rs", where)},
        "exposure_limit": lambda: {"exposure": exposure_at(block, where)},
        "bucket_cap": lambda: {"bucket_cap_rs": positive_setting(block, "bucket_cap_rs", where)},
        "open_risk_cap": lambda: {"open_risk_cap_rs": positive_setting(block, "open_risk_cap_rs", where)},
        "new_risk_per_day": lambda: {"new_risk_per_day_rs": positive_setting(block, "new_risk_per_day_rs", where)},
    }
    values = {}
    for rule in rules:
        values |= readers.get(rule, dict)()
    if any(rule in rules for rule in ("bucket_cap", "open_risk_cap", "new_risk_per_day")):
        values["bucket_sides"] = _sides(block, where)
    return values


def all_profiles(config: Mapping[str, Any]) -> dict[str, ProfileSettings]:
    """Every profile of `risk.profiles`, each checked, so a profile no run uses today is never wrong unnoticed."""
    names = get_setting(get_setting(config, "risk", ""), "profiles", "")
    return {name: profile_settings(config, name) for name in names}


def profile_settings(config: Mapping[str, Any], name: str) -> ProfileSettings:
    """The checked settings of risk profile `name` of an app config (`fno.config.load_app_config`)."""
    where = _where(name)
    block = get_setting(get_setting(get_setting(config, "risk", ""), "profiles", ""), name, ".profiles")
    rules = _rules(block, where)
    _check_keys(block, rules, where)
    profile = ProfileSettings(
        name, rules, positive_setting(block, "paper_account_rs", where),
        positive_setting(block, "max_loss_per_trade_rs", where), positive_setting(block, "drawdown_brake_rs", where),
        count_setting(block, AGE_DAYS, where) if AGE_DAYS in block else None,
        count_setting(block, AGE_SESSIONS, where) if AGE_SESSIONS in block else None,
        **_optional(block, rules, where),
    )  # fmt: skip
    caps = (profile.bucket_cap_rs, profile.open_risk_cap_rs, profile.new_risk_per_day_rs, profile.drawdown_brake_rs)
    if max(c or 0.0 for c in caps) > profile.paper_account_rs:
        raise RiskSettingsError(f"config.yaml risk{where}: a cap or the brake is larger than the paper account itself")
    return profile
