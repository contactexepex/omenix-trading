"""V4's and V5's history from their stored records (story G7b completion, parts c-e): the terms frozen each live day
(`v4/terms/<question>/<YYYY>/<date>.json`), V5's resolved outcomes (`v4/outcomes/v5/<YYYY>/<date>.json`, written once
with their source, its SHA-256 and first-seen time, protocol 1.5) and A16's live rows give each forecast day's outcome:
resolved, void or still unresolved. One place for both readers: the capture's base rates and G8's scoring."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, fields
from datetime import date, datetime

from ..forecast_v4.settlement import V5Outcome
from .option_outcomes import resolve_v4, v5_base_outcome
from .option_terms import OptionTerms, Void
from .series import Outcome, SessionRv

OUTCOMES_FOLDER = "v4/outcomes/v5"
DATE_FIELDS = frozenset({"day", "expiry"})


def outcome_path(day: date) -> str:
    return f"{OUTCOMES_FOLDER}/{day:%Y}/{day.isoformat()}.json"


def outcome_bytes(day: date, outcome: V5Outcome) -> bytes:
    return json.dumps({"day": day.isoformat(), **asdict(outcome)}, sort_keys=True, default=str).encode("utf-8")


def outcome_from_bytes(data: bytes) -> tuple[date, V5Outcome]:
    doc = json.loads(data)
    return date.fromisoformat(doc["day"]), V5Outcome(
        date.fromisoformat(doc["expiry"]), doc["inside"], doc["level"], doc["source"], doc["source_sha256"],
        datetime.fromisoformat(doc["first_seen_at"]),
    )  # fmt: skip


def terms_from_bytes(data: bytes) -> OptionTerms | Void:
    doc = json.loads(data)
    kind = Void if "reason" in doc else OptionTerms
    values = {f.name: doc[f.name] for f in fields(kind)}
    return kind(**{k: date.fromisoformat(v) if k in DATE_FIELDS else v for k, v in values.items()})


@dataclass(frozen=True)
class DayOutcome:
    value: bool | None  # None: void
    resolved_on: date


class OptionHistory:
    def __init__(self, v4_terms: Mapping[date, OptionTerms | Void], v5_terms: Mapping[date, OptionTerms | Void],
                 v5_outcomes: Mapping[date, V5Outcome], a16_rows: Sequence[SessionRv],
                 sessions: Sequence[date]):  # fmt: skip
        self.v4_terms, self.v5_terms, self.v5_outcomes = v4_terms, v5_terms, v5_outcomes
        self.a16_rows, self.sessions = a16_rows, sessions

    def v4(self) -> dict[date, DayOutcome]:
        """Each V4 day with void terms (void at once) or a resolved window; unresolved days are absent."""
        found = {}
        for day, terms in self.v4_terms.items():
            if isinstance(terms, Void):
                found[day] = DayOutcome(None, day)
            elif (result := resolve_v4(terms, self.a16_rows, self.sessions)) is not None:
                found[day] = DayOutcome(result.below, result.resolved_on)
        return found

    def v5(self) -> dict[date, DayOutcome]:
        found = {day: DayOutcome(None, day) for day, terms in self.v5_terms.items() if isinstance(terms, Void)}
        for day, outcome in self.v5_outcomes.items():
            found[day] = DayOutcome(outcome.inside, v5_base_outcome(day, outcome).resolved_on)
        return found

    def base_outcomes(self) -> tuple[list[Outcome], list[Outcome]]:
        """V4's and V5's non-void resolved outcomes, for their base rates."""
        v4 = [Outcome(d, o.value, o.resolved_on) for d, o in self.v4().items() if o.value is not None]
        v5 = [Outcome(d, o.value, o.resolved_on) for d, o in self.v5().items() if o.value is not None]
        return v4, v5

    def with_v5_outcomes(self, found: Mapping[date, V5Outcome]) -> OptionHistory:
        """This history with V5 outcomes just written added."""
        outcomes = {**self.v5_outcomes, **found}
        return OptionHistory(self.v4_terms, self.v5_terms, outcomes, self.a16_rows, self.sessions)

    def pending_v5(self) -> list[OptionTerms]:
        """V5 terms whose outcome is not written yet (the capture tries to resolve them)."""
        return [t for d, t in sorted(self.v5_terms.items()) if isinstance(t, OptionTerms) and d not in self.v5_outcomes]
