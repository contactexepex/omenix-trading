"""The exploratory back-fill of raw and premium-adjusted implied for V2 and V3 (story G7b completion, part b1;
PROTOCOL_v4.md sections 1.6 and 8): the EOD IV30 proxy of each day stands in for the pack's IV30, so every row is
`backfill_exploratory` and never pooled with live rows. It covers the scored sessions from 1 Jan 2024 that have a
close, before the first live day. Rows go to Drive only (CLAUDE.md, story O9), one write-once file per forecaster,
question, method hash and last day: a re-run of the same code on the same data writes the same bytes (a no-op); new
code or a later last day is a new file, never an overwrite."""

from __future__ import annotations

import hashlib
from datetime import date, timedelta

from ..constants import V2_RV_5S, V3_RV_20S, V4_BASELINE_PREMIUM_ADJUSTED, V4_BASELINE_RAW_IMPLIED
from ..forecast_v4.eligibility import PREMIUM_WINDOW_START
from ..forecast_v4.terms import HORIZON_SESSIONS
from .drive_records import backfill_path
from .implied import ImpliedBaselines, IvPoint, PremiumRatio, first_session_of_month, horizon_sums
from .records import BACKFILL, BASELINE, SLOT_REPORTED, Record, csv_text, record
from .series import DayValue

QUESTIONS = (V2_RV_5S, V3_RV_20S)
FORECASTERS = tuple((f, q) for q in QUESTIONS for f in (V4_BASELINE_RAW_IMPLIED, V4_BASELINE_PREMIUM_ADJUSTED))


class ImpliedBackfill:
    def __init__(self, eod_iv30: dict[date, IvPoint], close_rv: list[DayValue], sessions: list[date], method: str):
        """`close_rv`: the regular sessions' close-proxy `RV_s` (V2's and V3's measure, protocol 1.1); `sessions`:
        the scored sessions, far enough ahead for every horizon (a horizon past them is missing)."""
        self.eod, self.sessions, self.method = eod_iv30, sessions, method
        self.implied = {q: _baselines(HORIZON_SESSIONS[q], eod_iv30, close_rv, sessions) for q in QUESTIONS}

    def days(self, last_close: date, first_live: date | None) -> list[date]:
        """Scored sessions from 1 Jan 2024 to the last day whose inputs are all final, before the first live day:
        not after the last close, nor the last day with an EOD chain (a close archived before its chain would turn a
        missing value into a present one), nor the last day whose longest horizon ends inside the sessions (a
        calendar extended later would do the same). So the same data always gives the same rows and the same file."""
        last = min(last_close, max(self.eod, default=PREMIUM_WINDOW_START - timedelta(1)))
        reach = len(self.sessions) - max(HORIZON_SESSIONS[q] for q in QUESTIONS)
        last = min(last, self.sessions[reach - 1]) if reach > 0 else PREMIUM_WINDOW_START - timedelta(1)
        return [d for d in self.sessions if PREMIUM_WINDOW_START <= d <= last
                and (first_live is None or d < first_live)]  # fmt: skip

    def rows(self, days: list[date]) -> dict[tuple[str, str], list[Record]]:
        out: dict[tuple[str, str], list[Record]] = {key: [] for key in FORECASTERS}
        for d in days:
            iv = self.eod.get(d)
            for question, implied in self.implied.items():
                refit = first_session_of_month(d, self.sessions)
                values = {
                    V4_BASELINE_RAW_IMPLIED: (implied.raw(d, iv), self._inputs(d, iv)),
                    V4_BASELINE_PREMIUM_ADJUSTED: (implied.premium_adjusted(d, iv),
                                                   self._inputs(d, iv, refit, implied.ratio.at(refit))),
                }  # fmt: skip
                for forecaster, (value, inputs) in values.items():
                    out[(forecaster, question)].append(self._record(d, question, value, inputs))
        return out

    def write(self, rows: dict[tuple[str, str], list[Record]], put) -> list[str]:
        """`put(path, bytes)` saves one file write-once (O9's `DataStore.put`); returns the paths written."""
        paths = []
        for (forecaster, question), found in rows.items():
            if found:
                last = date.fromisoformat(max(r.day for r in found))
                paths.append(backfill_path(self.method, forecaster, question, last))
                put(paths[-1], csv_text(found).encode())
        return paths

    def _record(self, d: date, question: str, value, inputs: str) -> Record:
        return record(d, question, value.status, value.value, kind=BASELINE, slot=SLOT_REPORTED, label=BACKFILL,
                      method_sha256=self.method, inputs_sha256=inputs, made_at="")  # fmt: skip

    @staticmethod
    def _inputs(d: date, iv: IvPoint | None, refit: date | None = None, ratio: float | None = None) -> str:
        """SHA-256 of what decides the row: the day's IV30 point and, for premium-adjusted, its refit's ratio."""
        text = f"{d}|{None if iv is None else (repr(iv.value), iv.flagged)}|{refit}|{ratio!r}"
        return hashlib.sha256(text.encode()).hexdigest()


def _baselines(horizon: int, eod_iv30: dict[date, IvPoint], close_rv: list[DayValue], sessions: list[date]):
    return ImpliedBaselines(horizon, sessions, PremiumRatio(eod_iv30, horizon_sums(close_rv, horizon)))
