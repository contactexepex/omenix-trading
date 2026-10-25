"""Fires a routine once per batch and version (story O6). A version with a "fired" record is skipped; otherwise the
routine is fired and the record written. A failed fire leaves no record (the next run tries again); a fire whose
record Drive refused is reported, and the routine's own "processed" record makes the repeat fire harmless."""

from __future__ import annotations

from dataclasses import dataclass, field

from .pointer import BatchPointer
from .records import FIRED, PipelineRecords
from .trigger import FireFailed, RoutineTrigger

ALREADY_FIRED, FIRED_NOW, FIRE_FAILED, RECORD_REFUSED = "already fired", "fired", "fire failed", "record refused"


@dataclass(frozen=True)
class BatchOutcome:
    pointer: BatchPointer
    outcome: str  # one of the four outcomes above
    detail: str = ""  # the run's link, or why it failed

    @property
    def failed(self) -> bool:
        return self.outcome in (FIRE_FAILED, RECORD_REFUSED)


@dataclass
class DispatchReport:
    outcomes: list[BatchOutcome] = field(default_factory=list)

    def count(self, outcome: str) -> int:
        return sum(1 for o in self.outcomes if o.outcome == outcome)

    @property
    def failures(self) -> list[BatchOutcome]:
        return [o for o in self.outcomes if o.failed]


class BatchDispatcher:
    def __init__(self, records: PipelineRecords, trigger: RoutineTrigger):
        self.records, self.trigger = records, trigger

    def dispatch(self, pointers: list[BatchPointer]) -> DispatchReport:
        report = DispatchReport()
        for pointer in pointers:
            report.outcomes.append(self._one(pointer))
        return report

    def _one(self, pointer: BatchPointer) -> BatchOutcome:
        routine = self.trigger.name
        if self.records.has(FIRED, routine, pointer):
            return BatchOutcome(pointer, ALREADY_FIRED)
        try:
            link = self.trigger.fire(pointer)
        except FireFailed as error:
            return BatchOutcome(pointer, FIRE_FAILED, str(error))
        try:
            self.records.mark(FIRED, routine, pointer, run=link)
        except Exception as error:  # noqa: BLE001 - any refused Drive write is reported, never raised past the run
            return BatchOutcome(
                pointer, RECORD_REFUSED, f"fired, but Drive refused its record ({type(error).__name__})"
            )
        return BatchOutcome(pointer, FIRED_NOW, link)
