"""The scored sessions in a span, as the release run, the deadline run and G8's day labels list them (one helper)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta


def sessions_between(is_session: Callable[[date], bool]) -> Callable[[date, date], list[date]]:
    """`sessions(a, b)`: the days in [a, b] that `is_session` accepts, in order."""
    return lambda first, last: [first + timedelta(n) for n in range((last - first).days + 1)
                                if is_session(first + timedelta(n))]  # fmt: skip
