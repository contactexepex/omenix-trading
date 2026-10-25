"""G14's scoring report (story G14, criterion 6): each forecaster's live rows against A16's live intraday RV of the
next scored session (the V1 target G8 uses, `fno/forecast_scoring/v4/outcomes.py`), with v4's QLIKE
(`point_scores`, imported). Never a candle outcome: the target is read only from A16's live rows. A void target is
counted and left out; a target not yet recorded is pending. Descriptive only: no claim, no ranking for promotion."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from ..forecast_scoring.v4.scores import PointScores, point_scores
from ..forecast_v4_rules.baselines import OK
from ..forecast_v4_rules.candle_history import PairedRv
from ..forecast_v4_rules.records import LIVE
from .gap import gap_table
from .records import INPUT_MEASURE, V5Record

TITLE = "v5 side by side (G14): V1's forecasters on the spliced candle-first history; a measurement, no claim"
NOT_YET = "not enough data yet"
TABLE = ("| Forecaster | Rows | Scored | Void | Pending | No value | Mean QLIKE |", "|---|---|---|---|---|---|---|")


@dataclass(frozen=True)
class ForecasterScore:
    forecaster: str
    rows: int  # live rows written
    scored: int
    void: int  # target session void (A16 live)
    pending: int  # target session not recorded yet
    not_ok: int  # the forecaster gave no value that day
    scores: PointScores | None


def next_session(sessions: Sequence[date], d: date) -> date | None:
    later = [s for s in sessions if s > d]
    return min(later) if later else None


def score(name: str, rows: Mapping[str, V5Record], live: Mapping[date, float | None], sessions) -> ForecasterScore:
    pairs, void, pending, not_ok, written = [], 0, 0, 0, 0
    for row in rows.values():
        if row.label != LIVE:
            continue
        written += 1
        if row.status != OK:
            not_ok += 1
            continue
        target = next_session(sessions, date.fromisoformat(row.day))
        if target is None or target not in live:
            pending += 1
        elif live[target] is None:
            void += 1
        else:
            pairs.append((float(row.value), live[target]))
    return ForecasterScore(name, written, len(pairs), void, pending, not_ok, point_scores(pairs))


def render(scores: Sequence[ForecasterScore], pairs: Sequence[PairedRv]) -> list[str]:
    lines = [TITLE, f"Input: {INPUT_MEASURE}", *TABLE]
    for s in scores:
        qlike = f"{s.scores.mean_qlike:.6f}" if s.scores else NOT_YET
        lines.append(f"| {s.forecaster} | {s.rows} | {s.scored} | {s.void} | {s.pending} | {s.not_ok} | {qlike} |")
    return [*lines, "", *gap_table(pairs)]
