"""What one NSE index-list answer says (pure): its stamp, and each index's `last`, `open`, `high`, `low` and
`previous_close` (A4h-2). A list counts only when its stamp is today at or after 15:30 and each checked index's day
range holds its open and last (DR1's sanity check 5); any other answer is refused with a reason that holds no level.
INDIA VIX is recorded, never refused for its range: its findings are kept as the record's problems."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from .constants import (
    BASE_FIELDS,
    INDICES,
    LOW_ABOVE_HIGH,
    OUTSIDE_RANGE,
    RANGE_FIELDS,
    STAMP_FORMAT,
    STAMP_FROM,
    IndexName,
)


class Refused(Exception):
    """The answer is not today's close; the message names why (never a level)."""


@dataclass(frozen=True)
class ListRead:
    stamp: str  # NSE's text, e.g. "21-Oct-2026 15:30"
    values: dict[str, dict[str, float | None]]  # listed name -> {"last": .., "open": .., "high": .., ...}
    problems: dict[str, list[str]] = field(default_factory=dict)  # unchecked index -> its range findings


def read_answer(payload: dict, day: date) -> ListRead:
    stamp = str(payload.get("timestamp") or "").strip()
    if not stamp:
        raise Refused("NSE answer has no timestamp")
    try:
        stamped = datetime.strptime(stamp, STAMP_FORMAT)
    except ValueError as error:
        raise Refused(f"NSE stamp {stamp!r} is not readable") from error
    if stamped.date() != day:
        raise Refused(f"NSE stamp {stamp} is not today's session")
    if stamped.time() < STAMP_FROM:
        raise Refused(f"NSE stamp {stamp} is before {STAMP_FROM:%H:%M}")
    rows = {str(row.get("index", "")).strip(): row for row in payload.get("data") or ()}
    values = {name.listed: _values(rows, name) for name in INDICES}
    problems = {}
    for name in INDICES:
        found = range_problems(values[name.listed])
        if found and name.checked:
            raise Refused(f"{name.listed}: {found[0]}")
        if found:
            problems[name.listed] = found
    return ListRead(stamp, values, problems)


def range_problems(values: dict[str, float | None]) -> list[str]:
    """DR1's sanity check 5: the day's low not above its high, and the open and last inside [low, high] (edges in)."""
    high, low = values.get("high"), values.get("low")
    if high is None or low is None:
        return []
    if low > high:
        return [LOW_ABOVE_HIGH]
    return [OUTSIDE_RANGE.format(field=key) for key in BASE_FIELDS if not low <= values[key] <= high]


def _values(rows: dict, name: IndexName) -> dict[str, float | None]:
    row = rows.get(name.listed)
    if row is None:
        raise Refused(f"{name.listed} missing from the answer")
    required = {**BASE_FIELDS, **RANGE_FIELDS} if name.checked else BASE_FIELDS
    values = {key: _number(row, name.listed, nse, key in required) for key, nse in BASE_FIELDS.items()}
    return values | {key: _number(row, name.listed, nse, key in required) for key, nse in RANGE_FIELDS.items()}


def _number(row: dict, listed: str, nse: str, required: bool) -> float | None:
    try:
        return float(row[nse])
    except (KeyError, TypeError, ValueError) as error:
        if required:
            raise Refused(f"{listed} has no readable {nse}") from error
        return None


def difference(first: float, second: float) -> str:
    """`same`, or `differs by X` (a derived difference, never a level)."""
    gap = abs(first - second)
    return "same" if gap < 0.005 else f"differs by {gap:.2f}"
