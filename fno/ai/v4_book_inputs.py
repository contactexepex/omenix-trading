"""Story G11 (response 272): what the v4 firer gives each book, read from the committed records and the slot ledger.

- **The day's questions** are the ones the book's own slot (hybrid or ai_team) is registered for, from its
  `effective_start`: exactly the rows the look's reconciliation expects. One list, never an AI list; a registered
  question the book's prompt does not define is refused loudly (a misregistration), never silently dropped.
- **Hybrid's rules values:** the rules slot's registered forecaster and the primary baseline (G8's own series,
  `primary_values`, so V1 switches to HAR intraday exactly when G8 does), each its live row of the day (committed
  before 14:30); a missing row is `None` (no value), never a default.
- **The point questions' history** (G11 C4) from G8's own outcome series (`OutcomeSeries`, the one place for each
  measure): V1 the last `V1_HISTORY` intraday `RV_s`, V2 the last `V2_HISTORY` close-proxy `RV_s`, sessions before
  the day only."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ..constants import BOOK2_HYBRID, V1_RV_1S, V2_RV_5S, V4_SLOT_RULES
from ..forecast_scoring.v4.inputs import V4ForecastSource
from ..forecast_scoring.v4.outcomes import OutcomeSeries
from ..forecast_scoring.v4.primary import primary_values
from ..forecast_scoring.v4.records import SlotRegistry
from ..v4_pack.model import Pack
from .export import recent_closes
from .paths import CLOSES_FILE
from .v4_input import PRIMARY, V4InputFor, build_v4_input
from .v4_rows import SLOTS
from .versions import BookVersion

NOT_DEFINED = "{label} is registered for {questions}, which its prompt does not define: register a new version first"
V1_HISTORY, V2_HISTORY = 60, 260  # sessions of each point question's own measure shown (V2: as many as the closes)
RV_DIGITS = 6


@dataclass
class V4BookInputs:
    root: Path
    registry: SlotRegistry
    forecasts: V4ForecastSource
    series: OutcomeSeries  # G8's outcome series: each point question's history in its own measure

    def questions(self, version: BookVersion, day: date) -> list[str]:
        """The book's slot's started questions on `day` (every one gets a row, a refused one `not_fired`)."""
        slot = SLOTS[version.book]
        return sorted(q for (q, s), r in self.registry.registered().items() if s == slot and r.effective_start <= day)

    @staticmethod
    def refusal(version: BookVersion, questions: Sequence[str]) -> str:
        """Why the book cannot be asked `questions` (its prompt does not define one), or ''."""
        undefined = [q for q in questions if q not in version.questions]
        return NOT_DEFINED.format(label=version.label, questions=undefined) if undefined else ""

    def build(self, version: BookVersion, day: date, questions: Sequence[str], pack: Pack, pack_sha256: str) -> dict:
        who = V4InputFor(version.book, version.label, day, questions, pack_sha256)
        closes = recent_closes(self.root / CLOSES_FILE, day)
        hybrid = version.book == BOOK2_HYBRID
        rules = self._rules(day, questions) if hybrid else None
        widths = (version.envelope_width, version.point_envelope_width) if hybrid else None
        return build_v4_input(who, pack, closes, rules, widths, self._history(day, questions))

    def _rules(self, day: date, questions: Sequence[str]) -> dict[str, dict[str, float | None]]:
        registered = self.registry.registered()
        out = {}
        for question in questions:
            rule = registered.get((question, V4_SLOT_RULES))
            values = {rule.forecaster: _live(self.forecasts.values(question, rule.forecaster), day)} if rule else {}
            out[question] = values | {PRIMARY: _live(primary_values(question, self.forecasts), day)}
        return out

    def _history(self, day: date, questions: Sequence[str]) -> dict[str, dict[str, list]]:
        measures = {V1_RV_1S: (self.series.intraday_rv, V1_HISTORY), V2_RV_5S: (self.series.close_proxy_rv, V2_HISTORY)}
        out = {}
        for question in (q for q in questions if q in measures):
            read, count = measures[question]
            before = sorted((d, v) for d, v in read().items() if d < day)[-count:]
            out[question] = {"dates": [d.isoformat() for d, _ in before], "rv_s": [_significant(v) for _, v in before]}
        return out


def _significant(value: float | None) -> float | None:
    """An RV_s to `RV_DIGITS` significant digits: the routine retypes every digit, and more say nothing more."""
    return None if value is None else float(f"{value:.{RV_DIGITS}g}")


def _live(values: dict, day: date) -> float | None:
    found = values.get(day)
    return found.value if found is not None and found.live else None
