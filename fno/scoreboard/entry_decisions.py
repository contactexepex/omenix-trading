"""The committed decisions behind scoreboard B (story S2): every record of every run the desk used, with its D6
segment computed once over all of them (D6's pauses depend on the order), the record that opened each trade, and the
common start read from the records (S1's rule, never chosen by a person)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import date

from ..books.versions import Segment, Segments, Versions
from ..playbook.decision_record import NO_TRADE_ID, decision_facts
from .committed_runs import DayRun
from .entry_facts import EntryFacts, entry_facts
from .ports import OwnerOverrides


class EntryDecisions:
    def __init__(
        self, runs: Sequence[DayRun], records: Callable[[DayRun], list[dict]], versions: Versions,
        overrides: OwnerOverrides,
    ):  # fmt: skip
        self.runs, self.overrides = tuple(runs), overrides
        self._records: dict[tuple[str, date, str], dict] = {}
        facts = []
        for run in self.runs:
            for record in records(run):
                facts.append(decision_facts(record, run.commit))
                self._records[(run.book, run.day, record["opportunity_id"])] = record
        self.segments = Segments(versions, facts)

    def segment(self, book: str, day: date, opportunity_id: str) -> Segment | None:
        record = self._records.get((book, day, opportunity_id))
        return self.segments.segment_of(f"{record['run_id']}/{opportunity_id}") if record else None

    def entry(self, book: str, day: date, opportunity_id: str) -> EntryFacts | None:
        """The committed record that opened a trade on `day`; None when the desk used no such record."""
        record = self._records.get((book, day, opportunity_id))
        if record is None:
            return None
        return entry_facts(record, self.segment(book, day, opportunity_id), self.overrides.overridden(record))

    def structure(self, book: str, day: date, opportunity_id: str) -> str:
        """The structure code the record that opened a trade names (story S6's random control); empty when none."""
        record = self._records.get((book, day, opportunity_id)) or {}
        return (record.get("structure") or {}).get("structure", "")

    def common_start(self, books: Sequence[str]) -> date | None:
        """S1's rule: the first session on which every book has an on-time committed run made under a version
        registered before it (its day record is scored by D6); None until that day comes."""
        ready: dict[date, set[str]] = {}
        for run in self.runs:
            segment = self.segment(run.book, run.day, NO_TRADE_ID)
            if run.on_time and segment is not None and segment.scored:
                ready.setdefault(run.day, set()).add(run.book)
        days = [day for day, done in ready.items() if done >= set(books)]
        return min(days) if days else None
