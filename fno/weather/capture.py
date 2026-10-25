"""Writing the weather (story M1): today's live record before the cutoff (14:30, G10), and the exploratory back-fill.

- Live: only on a regular session (protocol v4 section 2), only for today and only before the 14:30 IST cutoff (as G7);
  otherwise nothing is written and the reason is printed. The US-move flag goes to the private Drive part only; the
  printed lines never show it (judge 129).
- Back-fill: every regular session from the first with inputs to the day before the first live record, labelled
  `backfill_exploratory` (protocol 8: 2017-26 is spent), with no `made_at` so a rerun writes identical files; no
  private part (no US flag is back-filled)."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable
from datetime import UTC, date, datetime

from ..forecast_v4_rules.capture import CUTOFF, CaptureRefused, cutoff
from ..forecast_v4_rules.records import BACKFILL, LIVE
from ..storage.raw_store import RawFileStore
from .day import WeatherDays
from .records import WeatherRecords, encode, red_share

PRIVATE_PATH = "weather/{d:%Y}/{d}.json"  # in the owner's Drive, derived area, beside the private cue tables
PRIVATE_SAVED = "private part saved to Drive"
PRIVATE_NOT_SAVED = "private part NOT saved to Drive: {why}"
BACKFILL_RED = "back-fill (exploratory): {days} days; colours {counts}; RED share {share:.1%}"
STALE_CLOSES = "the closes end at {latest}, not at the previous regular session {previous}: no weather (blocks trades)"
NOT_COUNTED = {"red_share": "not counted (back-fill)", "over_alarming": "not counted (back-fill)"}


def capture_weather(
    weather: WeatherDays, records: WeatherRecords, d: date, now: datetime, is_session: Callable[[date], bool],
    write_v4, us_flag: Callable[[], str], private: RawFileStore | None, previous: Callable[[date], date],
) -> list[str]:  # fmt: skip
    if d != now.date():
        raise CaptureRefused(f"{d} is not today ({now:%Y-%m-%d}): a live record is made on its own day only")
    if not is_session(d):
        raise CaptureRefused(f"{d} is not a v4 session (holiday, weekend, special or muhurat)")
    if now >= cutoff(d):
        raise CaptureRefused(f"{now:%Y-%m-%d %H:%M} IST is at or after {d}'s {CUTOFF:%H:%M} cutoff")
    if weather.latest_row(d) != previous(d):
        raise CaptureRefused(STALE_CLOSES.format(latest=weather.latest_row(d), previous=previous(d)))
    red = red_share(records.live_colours_before(d), weather.colours(d)[0])
    day = weather.day(d, LIVE, now.astimezone(UTC).isoformat(), red)
    records.write(d, day.public)
    added = sum(write_v4(f, q, [row]) for (f, q), row in day.rows.items())
    lines = [f"weather {d}: {day.public['colour']} ({day.public['proof']}); {added} v4 rows written"]
    return [*lines, _save_private(private, d, {"day": d.isoformat(), "us_move": us_flag()})]


def _save_private(store: RawFileStore | None, d: date, document: dict) -> str:
    if store is None:
        return PRIVATE_NOT_SAVED.format(why="the owner's Drive settings are not set")
    try:
        store.put(PRIVATE_PATH.format(d=d), encode(document))
    except Exception as error:  # noqa: BLE001 - the public record is already written; named by type only
        return PRIVATE_NOT_SAVED.format(why=type(error).__name__)
    return PRIVATE_SAVED


def backfill_weather(weather: WeatherDays, records: WeatherRecords, first_live: date | None, write_v4) -> list[str]:
    days = [d for d in weather.days[1:] if first_live is None or d < first_live]
    rows, colours = defaultdict(list), Counter()
    for d in days:
        day = weather.day(d, BACKFILL, "", NOT_COUNTED)
        records.write(d, day.public)
        colours[day.public["colour"]] += 1
        for key, row in day.rows.items():
            rows[key].append(row)
    added = sum(write_v4(f, q, found) for (f, q), found in rows.items())
    share = colours["RED"] / len(days) if days else 0.0
    counts = ", ".join(f"{c} {n}" for c, n in sorted(colours.items()))
    return [BACKFILL_RED.format(days=len(days), counts=counts, share=share), f"{added} v4 rows added"]
