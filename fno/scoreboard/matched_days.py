"""What each book did on each session's common opportunities (story S3, expected design 1): its action on every
opportunity of E2's set, or why the book or one opportunity is not observed that day. Not-observed days are never
scored; a book's misses (no run collected) count toward S1's miss cap, while days without a valid snapshot, days D6
leaves unscored, days without a common pack and Book 3's days before F7 are counted apart."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from ..constants import BOOK3_AI
from ..desk.pack_store import PackStore
from ..playbook.decision_record import NO_TRADE_ID
from .committed_runs import DayRun
from .entry_decisions import EntryDecisions
from .matched_actions import NOT_OBSERVED, Action, action_of
from .ports import MatchedShadowDecisions

NO_SNAPSHOT, NO_PACK, NO_RUN, UNSCORED, F7_NOT_BUILT = (
    "no valid execution snapshot",
    "no common pack",
    "no run collected",
    "unscored (D6)",
    "F7 not built",
)
MISSES = frozenset({NO_RUN})  # the only reason that counts toward the miss cap (design 6)
NO_RECORD, OTHER_PACK = "no record for this opportunity", "record names another common pack"


@dataclass(frozen=True)
class CommonSet:
    sha256: str
    opportunities: tuple[Mapping, ...]  # E2's entries, "no trade" left out


@dataclass(frozen=True)
class BookDay:
    book: str
    day: date
    observed_reason: str = ""  # empty when observed
    actions: dict[str, Action] = field(default_factory=dict)  # opportunity ID -> action
    segment: str = ""

    @property
    def observed(self) -> bool:
        return not self.observed_reason


class CommonPacks:
    """E2's common opportunity set of a day, from the committed common pack, with the SHA-256 of its bytes."""

    def __init__(self, root: Path):
        self.store = PackStore(root)

    def day(self, day: date) -> CommonSet | None:
        path = self.store.common_path(day)
        if not path.is_file():
            return None
        data = path.read_bytes()
        entries = json.loads(data)["opportunities"]
        found = tuple(e for e in entries if e["opportunity_id"] != NO_TRADE_ID)
        return CommonSet(hashlib.sha256(data).hexdigest(), found)


class MatchedDays:
    def __init__(self, runs: Sequence[DayRun], records: Callable[[DayRun], list[dict]], decisions: EntryDecisions,
                 packs: Callable[[date], CommonSet | None], snapshot_days: set[date],
                 shadow: MatchedShadowDecisions):  # fmt: skip
        self.runs = {(r.book, r.day): r for r in runs if r.on_time}
        self.records, self.decisions, self.packs = records, decisions, packs
        self.snapshot_days, self.shadow = snapshot_days, shadow

    def book_day(self, book: str, day: date) -> BookDay:
        common = self.packs(day)
        if day not in self.snapshot_days:
            return BookDay(book, day, NO_SNAPSHOT)
        if common is None:
            return BookDay(book, day, NO_PACK)
        if book == BOOK3_AI:
            entries = self.shadow.records(day)
            return BookDay(book, day, F7_NOT_BUILT) if entries is None else self._actions(book, day, entries, common)
        run = self.runs.get((book, day))
        if run is None:
            return BookDay(book, day, NO_RUN)
        segment = self.decisions.segment(book, day, NO_TRADE_ID)
        if segment is None or not segment.scored:
            return BookDay(book, day, UNSCORED)
        return self._actions(book, day, self.records(run), common, segment.label)

    def _actions(self, book: str, day: date, records: list[dict], common: CommonSet, segment: str = "") -> BookDay:
        by_id = {r["opportunity_id"]: r for r in records}
        actions = {}
        for entry in common.opportunities:
            record = by_id.get(entry["opportunity_id"])
            if record is None:
                actions[entry["opportunity_id"]] = Action(NOT_OBSERVED, NO_RECORD)
            elif record.get("common_pack_sha256") != common.sha256:
                actions[entry["opportunity_id"]] = Action(NOT_OBSERVED, OTHER_PACK, record)
            else:
                actions[entry["opportunity_id"]] = action_of(record)
        return BookDay(book, day, actions=actions, segment=segment)
