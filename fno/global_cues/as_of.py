"""The cue value an NSE session may use at a cutoff on its India date (story A17).

Two cutoffs (design 2.1; orchestrator, 15 Oct 2026), chosen explicitly:
- `OPEN` (09:15 IST): what was known before the open, for overnight gaps;
- `DECISION` (15:00 IST): what was known at the desk's decision time; it adds the same day's USD/INR reference rate,
  published at about 13:00-13:30 IST.

Two views:
- research (`live_only=False`): a value is usable when its source's rule says it was final and published before the
  cutoff (`available_at`: the US close at 16:00 US Eastern, so 01:30 IST in US summer time and 02:30 IST in winter on
  the next day; the Treasury yield by 18:00 US Eastern, an assumption; the reference rate at 13:30 IST; Brent by the
  end of the 10th day after its date, an assumption). For back-filled history, where nothing was observed live.
- live (`live_only=True`): a value is usable when this tool first saw it before the cutoff (`first_seen_at`): an
  observation, exact. A value seen before it was final never became a row (`collection.final_values`).
A US holiday simply has no row, so a Tuesday after a US Monday holiday gets Friday's close.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, time

from ..models import IST

OPEN, DECISION = time(9, 15), time(15, 0)


def value_for(
    rows: list[dict[str, str]],
    india_day: date,
    cutoff: time,
    live_only: bool,
    available_at: Callable[[date], datetime],
) -> dict[str, str] | None:
    """The newest row usable on `india_day` at `cutoff` (IST), or None when there is none."""
    moment = datetime.combine(india_day, cutoff, tzinfo=IST)

    def known(row: dict[str, str]) -> datetime:
        return (
            datetime.fromisoformat(row["first_seen_at"])
            if live_only
            else available_at(date.fromisoformat(row["value_date"]))
        )

    usable = [r for r in rows if known(r) < moment]
    return max(usable, key=lambda r: r["value_date"], default=None)
