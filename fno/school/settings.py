"""The school's settings (story MS-P1a): the `school` block of config.yaml, read with exactly these keys.

Separate switches (response 327 section 3): `enabled` gates every paper decision, `reports` the two report sections;
both default off. Limits are rupees; none may be negative. A missing or unknown key is an error, never a default."""

from dataclasses import dataclass, fields
from datetime import date

from .constants import SETTINGS_KEY


class SchoolSettingsError(ValueError):
    """The `school` block is missing, holds an unknown key, or a value of the wrong kind."""


@dataclass(frozen=True)
class SchoolSettings:
    enabled: bool
    reports: bool
    first_counted: date | None  # the first counted session, set from the frozen comparison card (MS-P1h)
    account_rs: int  # each driver version's paper account
    max_loss_rs: int  # per trade, every charge and pad included
    daily_stop_rs: int  # realised plus marked loss since the previous slot that stops new entries for the session
    brake_rs: int  # equity below its high that pauses new entries until a monthly review row lifts it
    max_new_trades_per_slot: int
    bucket_rs: int
    open_risk_rs: int
    new_risk_day_rs: int


_SWITCHES = ("enabled", "reports")
_LIMITS = tuple(f.name for f in fields(SchoolSettings) if f.name not in (*_SWITCHES, "first_counted"))


def school_settings(config: dict) -> SchoolSettings:
    block = config.get(SETTINGS_KEY)
    if not isinstance(block, dict):
        raise SchoolSettingsError(f"config.yaml has no `{SETTINGS_KEY}` block")
    expected = {f.name for f in fields(SchoolSettings)}
    if set(block) != expected:
        unknown, missing = sorted(set(block) - expected), sorted(expected - set(block))
        raise SchoolSettingsError(f"`{SETTINGS_KEY}` keys wrong: unknown {unknown}, missing {missing}")
    for key in _SWITCHES:
        if not isinstance(block[key], bool):
            raise SchoolSettingsError(f"`{SETTINGS_KEY}.{key}` must be true or false")
    for key in _LIMITS:
        value = block[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise SchoolSettingsError(f"`{SETTINGS_KEY}.{key}` must be a whole number, zero or more")
    return SchoolSettings(**{**block, "first_counted": _day(block["first_counted"])})


def _day(value) -> date | None:
    if value is None or isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise SchoolSettingsError(f"`{SETTINGS_KEY}.first_counted` must be a date (YYYY-MM-DD) or empty") from exc
