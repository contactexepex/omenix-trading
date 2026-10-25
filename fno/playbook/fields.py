"""Reading a playbook document field by field, so that every refusal names the exact field (story D1 criterion 1)."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from datetime import date


class PlaybookError(ValueError):
    """A playbook file, the registry or a status change is refused; `field` names what is wrong."""

    def __init__(self, field: str, reason: str):
        super().__init__(f"{field}: {reason}")
        self.field, self.reason = field, reason


class Fields:
    """One mapping of a document, with its dotted path for error messages. Keys must match exactly: a missing field
    and an unknown field (a typo would otherwise be silently ignored) are both refused."""

    def __init__(self, values: object, path: str, keys: Collection[str]):
        if not isinstance(values, Mapping):
            raise PlaybookError(path or "document", "must be a mapping of fields")
        missing = [key for key in keys if key not in values]
        if missing:
            raise PlaybookError(self._join(path, missing[0]), "missing field")
        unknown = sorted(str(key) for key in values if key not in keys)
        if unknown:
            raise PlaybookError(self._join(path, unknown[0]), "unknown field")
        self.values, self.path = values, path

    @staticmethod
    def _join(path: str, key: str) -> str:
        return f"{path}.{key}" if path else key

    def name(self, key: str) -> str:
        return self._join(self.path, key)

    def refuse(self, key: str, reason: str) -> PlaybookError:
        return PlaybookError(self.name(key), reason)

    def section(self, key: str, keys: Collection[str]) -> Fields:
        return Fields(self.values[key], self.name(key), keys)

    def raw(self, key: str) -> object:
        return self.values[key]

    def text(self, key: str) -> str:
        value = self.values[key]
        if not isinstance(value, str) or not value.strip():
            raise self.refuse(key, "must be non-empty text")
        return value.strip()

    def optional_text(self, key: str) -> str | None:
        return None if self.values[key] is None else self.text(key)

    def number(self, key: str, positive: bool = False) -> float:
        value = self.values[key]
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise self.refuse(key, "must be a number")
        if positive and value <= 0:
            raise self.refuse(key, "must be above zero")
        return float(value)

    def whole(self, key: str, minimum: int) -> int:
        value = self.values[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            raise self.refuse(key, f"must be a whole number of at least {minimum}")
        return value

    def day(self, key: str) -> date:
        value = self.values[key]
        if not isinstance(value, date):
            raise self.refuse(key, "must be a date (YYYY-MM-DD)")
        return value

    def optional_day(self, key: str) -> date | None:
        return None if self.values[key] is None else self.day(key)

    def choice(self, key: str, allowed: Collection[str]) -> str:
        value = self.values[key]
        if value not in allowed:
            raise self.refuse(key, f"unknown value {value!r}; allowed: {sorted(allowed)}")
        return value

    def items(self, key: str, keys: Collection[str], non_empty: bool = False) -> list[Fields]:
        values = self._list(key, non_empty)
        return [Fields(value, f"{self.name(key)}[{n}]", keys) for n, value in enumerate(values)]

    def texts(self, key: str) -> tuple[str, ...]:
        values = self._list(key, non_empty=True)
        if not all(isinstance(value, str) and value.strip() for value in values):
            raise self.refuse(key, "every entry must be non-empty text")
        return tuple(value.strip() for value in values)

    def days(self, key: str) -> tuple[date, ...]:
        values = self._list(key, non_empty=True)
        if not all(isinstance(value, date) for value in values) or list(values) != sorted(set(values)):
            raise self.refuse(key, "must be dates (YYYY-MM-DD) in increasing order, no repeats")
        return tuple(values)

    def _list(self, key: str, non_empty: bool) -> list:
        values = self.values[key]
        if not isinstance(values, list) or (non_empty and not values):
            raise self.refuse(key, "must be a non-empty list" if non_empty else "must be a list")
        return values
