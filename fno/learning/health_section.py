"""The data-health section (story LR1; design 2.1's layer-1 metrics), per session of the week, from committed files
only: the 3 pm capture (its `.canonical` marker, the sidecar's `complete` and the minutes after 14:55 IST it finished),
the daily card (T1's own `misses`, the same words the next card uses) and the weather record; then A16's live
session count against V1's 20-session minimum. The v4 forecasts' missed days are G9's miss lines in the forecasts
section, not counted again here."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, time

from ..cards.deliveries import DeliveryLog, misses
from ..models import IST
from .readers import CaptureSource, CaptureState, SessionCount
from .report import PostMortemSection
from .week import Week

CAPTURE_DUE = time(14, 55)
A16_MINIMUM = 20  # REPLAN slice A: V1 needs 20 sessions of A16
NO_SESSION = "no NSE regular session this week"


class DataHealthSection(PostMortemSection):
    name = "data_health"

    def __init__(self, captures: CaptureSource, cards: DeliveryLog, has_weather: Callable[[date], bool],
                 intraday: SessionCount):  # fmt: skip
        self.captures, self.cards, self.has_weather, self.intraday = captures, cards, has_weather, intraday

    def lines(self, week: Week) -> list[str]:
        rows = self._rows(week)
        lines = ["*Data health*"]
        if not rows:
            return [*lines, NO_SESSION, self._a16_line()]
        lines += [f"- {r['day']}: 3 pm quotes {r['capture']}; card {r['card']}; weather record {r['weather']}"
                  for r in rows]  # fmt: skip
        whole = sum(r["capture_complete"] and r["card"] == "ok" and r["weather"] == "yes" for r in rows)
        return [*lines, f"Complete days (capture, card and weather record): {whole} of {len(rows)}", self._a16_line()]

    def data(self, week: Week) -> dict:
        return {"days": self._rows(week), "a16_sessions": self.intraday.count()}

    def _rows(self, week: Week) -> list[dict]:
        return [self._row(d) for d in week.sessions]

    def _row(self, day: date) -> dict:
        capture = self.captures.capture(day)
        card = misses(self.cards, day)
        return {"day": day.isoformat(), "capture": _capture_words(day, capture),
                "capture_complete": bool(capture and capture.complete), "card": "; ".join(card) if card else "ok",
                "weather": "yes" if self.has_weather(day) else "missing"}  # fmt: skip

    def _a16_line(self) -> str:
        n = self.intraday.count()
        state = f"not enough data yet ({n} of {A16_MINIMUM})" if n < A16_MINIMUM else f"{n} sessions"
        return f"15-minute recorder (A16) live sessions: {state}"


def _capture_words(day: date, capture: CaptureState | None) -> str:
    if capture is None:
        return "none"
    if capture.finished_at is None:
        return f"complete={capture.complete}, no finish time"
    due = datetime.combine(day, CAPTURE_DUE, IST)
    late = (capture.finished_at - due).total_seconds() / 60
    return f"complete={capture.complete}, finished {late:.1f} minutes after 14:55"
