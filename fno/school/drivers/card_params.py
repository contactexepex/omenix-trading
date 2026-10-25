"""Typed reads of a driver card's `parameters` (story MS-P1e). A card is a frozen file: a missing or mistyped value
is an error naming the card and the key when the driver is built, never a default that quietly changes a rule."""

from collections.abc import Mapping

from ..contracts.decisions import DriverCard


class CardError(ValueError):
    """A card parameter is missing or of the wrong kind."""


class CardParams:
    def __init__(self, card: DriverCard):
        self.card_id, self._values = card.driver_id, card.parameters

    def number(self, key: str) -> float:
        value = self._require(key)
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise CardError(f"{self.card_id}: `{key}` must be a number, not {value!r}")
        return float(value)

    def whole(self, key: str) -> int:
        value = self.number(key)
        if value != int(value):
            raise CardError(f"{self.card_id}: `{key}` must be a whole number, not {value!r}")
        return int(value)

    def text(self, key: str) -> str:
        value = self._require(key)
        if not isinstance(value, str):
            raise CardError(f"{self.card_id}: `{key}` must be text, not {value!r}")
        return value

    def number_or_none(self, key: str) -> float | None:
        """A rule the card leaves out does not apply; one it writes must be a number."""
        return self.number(key) if key in self._values else None

    def whole_or_none(self, key: str) -> int | None:
        return self.whole(key) if key in self._values else None

    def _require(self, key: str):
        if key not in self._values:
            raise CardError(f"{self.card_id}: the card has no `{key}`")
        return self._values[key]


def parameters_of(values: Mapping) -> dict[str, float | int | str]:
    """A card file's parameter block, checked to hold only numbers and text."""
    bad = [k for k, v in values.items() if isinstance(v, bool) or not isinstance(v, int | float | str)]
    if bad:
        raise CardError(f"card parameters must be numbers or text: {sorted(bad)}")
    return dict(values)
