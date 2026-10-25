"""Firing the AI books' decision routines (story F1t, O1's `ai_fire` step, right after the pack): one pointer per live
book through its routine's trigger (O6's `RoutineTrigger`), fired once a day across crashes (`FireOnceLog`). For each
book the first of these that applies is recorded as `not_fired` with its reason: the budget stop (BG1), no registered
decision version, the stop rule (two transcript breaches in 20 decision days), the day's packs missing, a start after
`latest_fire`, a pointer over its cap, or a pointer the public-record scan flags. The fire log keeps each book's labels
(never a pack or a card), so the collection can check the answer against exactly what was fired."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from ..ai.audit_plan import FIRED_SUFFIX
from ..ai.budget_stop import BudgetCheck, BudgetStop
from ..ai.fire_once import Commit, FireOnceLog
from ..ai.run_terms import RunTerms
from ..pipeline.trigger import FireFailed, RoutineTrigger
from ..record_scan.scanner import RecordScanner
from .answer import labels_of
from .figures import texts as texts_of
from .model_audit import decision_stop_reason
from .paths import DECISIONS_FOLDER, fired_path
from .pointer import MAX_POINTER_BYTES, DecisionPointer
from .ports import AnalystCards, DayPacks
from .versions import DecisionRegistry, VersionRefused

NO_PACKS = "the day's packs are not written ({why}): nothing to decide from"
LATE_START = "the fire step started {now:%H:%M:%S}, after {latest:%H:%M:%S}: its answer could only be late"
TOO_BIG = "the pointer is {size} bytes, over the {cap}-byte cap: not sent (never truncated)"
FLAGGED = "the pointer holds what the public-record scan flags ({kinds}): not sent"


@dataclass(frozen=True)
class FireTiming:
    latest_fire: datetime  # a fire step starting later fires nothing
    receipt_deadline: datetime  # both travel in the pointer: the routine reads no config
    reveal_from: datetime


class DecisionFirer:
    def __init__(self, root: Path, registry: DecisionRegistry, triggers: Mapping[str, RoutineTrigger],
                 budget: BudgetStop, packs: DayPacks, cards: AnalystCards, scanner: RecordScanner,
                 commit: Commit, clock: Callable[[], datetime], terms: RunTerms):  # fmt: skip
        self.root, self.registry, self.triggers, self.budget = Path(root), registry, dict(triggers), budget
        self.terms = terms  # the decision run's (`terms.decision_terms`): the stop rule reads its audits
        self.budget_note = ""  # the day's BG1 reading failed: fired anyway, said in the step's alert
        self.packs, self.cards, self.scanner, self.commit, self.clock = packs, cards, scanner, commit, clock

    def fire(self, day: date, books: Sequence[str], timing: FireTiming) -> dict[str, dict]:
        """Every live book's fire log entry for the day; the caller commits `fired_path(day)`."""
        log = FireOnceLog(self.root, fired_path(day), self.commit, self.clock)
        if log.read():
            return log.fire({}, self._never, "F1t fire")  # a rerun: nothing is fired again
        pointers, planned = {}, {}
        budget = self.budget.check(day)  # once a day, for every book
        self.budget_note = budget.note
        for book in books:
            pointer, entry = self._plan(day, book, timing, budget)
            planned[book] = entry
            if pointer is not None:
                pointers[book] = pointer
        return log.fire(planned, lambda book: self._fire_one(book, pointers[book]), f"F1t {day} decision fire")

    def _plan(
        self, day: date, book: str, timing: FireTiming, budget: BudgetCheck
    ) -> tuple[DecisionPointer | None, dict]:
        if budget.stop:
            return None, {"reason": budget.stop}
        try:
            version = self.registry.current(book)
        except VersionRefused as missing:
            return None, {"reason": str(missing)}
        entry = {"version": version.label}
        stopped = decision_stop_reason(self.root, book, version.label, day, self.terms, decision_days(self.root))
        if stopped:
            return None, entry | {"reason": stopped}
        try:
            common, private = self.packs.common(day), self.packs.private(book, day)
        except (OSError, ValueError) as missing:
            return None, entry | {"reason": NO_PACKS.format(why=f"{type(missing).__name__}: {missing}")}
        if self.clock() > timing.latest_fire:
            return None, entry | {"reason": LATE_START.format(now=self.clock(), latest=timing.latest_fire)}
        item = self.cards.item(day, version.role_units)
        pointer = DecisionPointer(
            book, day, version.label, common.sha256, private.body, item, timing.receipt_deadline, timing.reveal_from
        )
        refusal = self._refusal(pointer)
        if refusal:
            return None, entry | {"reason": refusal}
        return pointer, entry | {"fire": True, "labels": labels_of(pointer), "pointer_bytes": pointer.size()}

    def _refusal(self, pointer: DecisionPointer) -> str:
        if pointer.size() > MAX_POINTER_BYTES:
            return TOO_BIG.format(size=pointer.size(), cap=MAX_POINTER_BYTES)
        texts = [("decision pointer", pointer.to_text()), *texts_of(json.loads(pointer.to_text()), "decision pointer")]
        findings = [f for place, text in texts for f in self.scanner.scan_text(place, text)]  # decoded: JSON escapes
        return FLAGGED.format(kinds=", ".join(sorted({f.kind for f in findings}))) if findings else ""  # hide nothing

    def _fire_one(self, book: str, pointer: DecisionPointer) -> dict:
        trigger = self.triggers.get(book)
        if trigger is None:
            return {"fired": False, "reason": f"no routine trigger wired for {book}"}
        try:
            return {"fired": True, "session": trigger.fire(pointer)}
        except FireFailed as failed:
            return {"fired": False, "reason": str(failed)}

    @staticmethod
    def _never(book: str) -> dict:
        raise AssertionError(f"{book}: a rerun never fires")


def decision_days(root: Path) -> list[date]:
    """The days with a decision fire log, oldest first: the stop rule's 20-day window counts these."""
    logs = (Path(root) / DECISIONS_FOLDER).glob(f"*/*{FIRED_SUFFIX}")
    return sorted(date.fromisoformat(path.name.removesuffix(FIRED_SUFFIX)) for path in logs)
