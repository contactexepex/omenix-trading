"""Typed reads of an idea card's ```factory block (story R1): every refusal names the card and the field, and no field
has a default (judge 261: a card lacking an input is refused by name when its gate runs)."""

from __future__ import annotations

import re
from collections.abc import Iterable

_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class CardError(ValueError):
    """The card is refused; the message names the card and the field."""


class Fields:
    def __init__(self, values: dict, where: str, prefix: str = ""):
        if not isinstance(values, dict):
            raise CardError(f"{where}: field {prefix.rstrip('.') or 'block'!r} must be a mapping of fields")
        self.values, self.where, self.prefix = values, where, prefix

    def refuse(self, key: str, problem: str) -> CardError:
        return CardError(f"{self.where}: field '{self.prefix}{key}' {problem}")

    def only(self, allowed: Iterable[str]) -> Fields:
        unknown = sorted(set(self.values) - set(allowed))
        if unknown:
            raise CardError(f"{self.where}: unknown field '{self.prefix}{unknown[0]}'")
        return self

    def has(self, key: str) -> bool:
        return self.values.get(key) is not None

    def raw(self, key: str):
        if not self.has(key):
            raise self.refuse(key, "is missing")
        return self.values[key]

    def text(self, key: str) -> str:
        value = self.raw(key)
        if not isinstance(value, str) or not value.strip():
            raise self.refuse(key, "must be non-empty text")
        return " ".join(value.split())

    def slug(self, key: str) -> str:
        value = self.text(key)
        if not _SLUG.match(value):
            raise self.refuse(key, "must be lower-case letters, digits and hyphens")
        return value

    def choice(self, key: str, options: Iterable[str]) -> str:
        value, options = self.text(key), tuple(options)
        if value not in options:
            raise self.refuse(key, f"must be one of {', '.join(options)}")
        return value

    def flag(self, key: str) -> bool:
        value = self.raw(key)
        if not isinstance(value, bool):
            raise self.refuse(key, "must be yes or no")
        return value

    def count(self, key: str) -> int:
        value = self.raw(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise self.refuse(key, "must be a whole number of at least 1")
        return value

    def number(self, key: str) -> float:
        value = self.raw(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise self.refuse(key, "must be a number")
        return float(value)

    def positive(self, key: str) -> float:
        value = self.number(key)
        if value <= 0:
            raise self.refuse(key, "must be above zero")
        return value

    def not_negative(self, key: str) -> float:
        value = self.number(key)
        if value < 0:
            raise self.refuse(key, "must be zero or more")
        return value

    def probability(self, key: str) -> float:
        value = self.number(key)
        if not 0 <= value <= 1:
            raise self.refuse(key, "must be a probability between 0 and 1")
        return value

    def section(self, key: str) -> Fields:
        return Fields(self.raw(key), self.where, f"{self.prefix}{key}.")

    def sections(self, key: str) -> list[Fields]:
        values = self.raw(key)
        if not isinstance(values, list) or not values:
            raise self.refuse(key, "must be a non-empty list")
        return [Fields(value, self.where, f"{self.prefix}{key}[{n}].") for n, value in enumerate(values)]

    def texts(self, key: str) -> list[str]:
        values = self.raw(key)
        if not isinstance(values, list) or not values or not all(isinstance(v, str) and v.strip() for v in values):
            raise self.refuse(key, "must be a non-empty list of text")
        return [" ".join(v.split()) for v in values]
