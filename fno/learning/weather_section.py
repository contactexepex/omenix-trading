"""The weather section (story LR1): each session's M1 record as written (operative colour, the v0 colour beside it,
label and status), the next-session V6a outcome from G7's one rule (`series.big_move_outcomes`, as G8 resolves it),
the weather misses (design 4.3: a GREEN day followed by a 2% move) and the RED share M1 wrote on its latest live
record. Weather's scores are in the forecasts section (G8 scores weather_vix_v1 and weather_checklist_v0)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import date

from ..forecast_v4_rules.records import LIVE
from ..weather.constants import WeatherColour
from ..weather.records import WeatherRecords
from .report import PostMortemSection
from .week import Week

MISSING, UNRESOLVED = "missing", "unresolved"
NO_LIVE = "RED share: no live weather record this week"


class WeatherSection(PostMortemSection):
    name = "weather"

    def __init__(self, records: WeatherRecords, big_move_next: Callable[[], Mapping[date, bool]]):
        self.records, self.big_move_next = records, big_move_next  # day -> a 2% move in the next session

    def lines(self, week: Week) -> list[str]:
        rows = self._rows(week)
        lines = ["*Weather*"]
        lines += [f"- {r['day']}: {r['colour']} (v0 {r['v0_colour']}; {r['label']}, {r['status']}); next session "
                  f"2% move: {r['big_move']}" for r in rows]  # fmt: skip
        lines += [_tally(rows), _misses(rows), _red_share(self._latest_live(week))]
        return lines

    def data(self, week: Week) -> dict:
        rows = self._rows(week)
        return {"days": rows, "misses": [r["day"] for r in rows if _is_miss(r)]}

    def _rows(self, week: Week) -> list[dict]:
        moves = self.big_move_next()
        return [_row(d, self.records.for_day(d), moves) for d in week.sessions]

    def _latest_live(self, week: Week) -> dict | None:
        found = [self.records.for_day(d) for d in week.sessions]
        return next((r for r in reversed(found) if r and r["label"] == LIVE), None)


def _row(day: date, record: dict | None, moves: Mapping[date, bool]) -> dict:
    move = UNRESOLVED if day not in moves else "yes" if moves[day] else "no"
    if record is None:
        return {"day": day.isoformat(), "colour": MISSING, "v0_colour": MISSING, "label": MISSING, "status": MISSING,
                "big_move": move}  # fmt: skip
    return {"day": day.isoformat(), "colour": record["colour"], "v0_colour": record["v0_colour"],
            "label": record["label"], "status": record["status"], "big_move": move}  # fmt: skip


def _is_miss(row: dict) -> bool:
    return row["colour"] == WeatherColour.GREEN and row["big_move"] == "yes"


def _tally(rows: list[dict]) -> str:
    parts = []
    for colour in (*WeatherColour, MISSING):
        days = [r for r in rows if r["colour"] == colour]
        if days:
            moved = sum(r["big_move"] == "yes" for r in days)
            parts.append(f"{colour} {len(days)} days, {moved} with a 2% move")
    return "Colours this week: " + ("; ".join(parts) if parts else "no session")


def _misses(rows: list[dict]) -> str:
    days = [r["day"] for r in rows if _is_miss(r)]
    return "Weather misses (GREEN, then a 2% move): " + (", ".join(days) if days else "none")


def _red_share(record: dict | None) -> str:
    if record is None:
        return NO_LIVE
    share = record["red_share"]
    shown = f"{share:.1%}" if isinstance(share, float) else share
    return f"RED share of the last 250 live records: {shown}; over-alarming: {record['over_alarming']}"
