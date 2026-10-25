"""When a 3 pm capture runs (story A4e). A4's own window (14:55-15:10) is the default and never changes; a named window
from `config.yaml` `quotes.windows` (protocol v4's 14:30-14:40) is a second capture in its own dataset, so no reader
of the default capture can see it."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time

from ..config import ConfigError

WINDOWS_KEY = "windows"
V4_WINDOW = "v4"  # protocol v4's 14:30-14:40 pack window (stories A4e, G10)
KEYS = ("start", "end", "max_early_wait_minutes")
UNKNOWN = "quotes.windows has no window named {name!r} (config.yaml)"
BAD_KEYS = "quotes.windows.{name} needs exactly the keys {keys} (config.yaml)"
BAD_TIME = "quotes.windows.{name}.{key} is not a time HH:MM: {value!r} (config.yaml)"
BAD_ORDER = "quotes.windows.{name}: start {start} is not before end {end} (config.yaml)"
BAD_WAIT = "quotes.windows.{name}.max_early_wait_minutes is not a whole number of minutes: {value!r} (config.yaml)"


@dataclass(frozen=True)
class QuoteWindow:
    name: str  # "" is A4's default window
    start: time
    end: time
    max_early_wait_seconds: int

    @property
    def named(self) -> bool:
        return bool(self.name)

    def dataset(self, base: str) -> str:
        """The default window keeps A4's dataset; a named one has its own folder beside it."""
        return f"{base}-{self.name}" if self.named else base


def named_window(cfg: dict, name: str) -> QuoteWindow:
    """The named window from the app's settings; refused (ConfigError) before any request when it is missing or bad."""
    quotes = cfg.get("quotes")
    windows = quotes.get(WINDOWS_KEY) if isinstance(quotes, dict) else None
    entry = windows.get(name) if isinstance(windows, dict) else None
    if entry is None:
        raise ConfigError(UNKNOWN.format(name=name))
    if not isinstance(entry, dict) or set(entry) != set(KEYS):
        raise ConfigError(BAD_KEYS.format(name=name, keys=", ".join(KEYS)))
    start, end = (_time(name, key, entry[key]) for key in ("start", "end"))
    if start >= end:
        raise ConfigError(BAD_ORDER.format(name=name, start=start, end=end))
    wait = entry["max_early_wait_minutes"]
    if isinstance(wait, bool) or not isinstance(wait, int) or wait < 0:
        raise ConfigError(BAD_WAIT.format(name=name, value=wait))
    return QuoteWindow(name, start, end, wait * 60)


def _time(name: str, key: str, value) -> time:
    try:
        return datetime.strptime(str(value), "%H:%M").time()
    except ValueError:
        raise ConfigError(BAD_TIME.format(name=name, key=key, value=value)) from None
