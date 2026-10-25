"""The market school's sealed decisions of the day as a candidate source (story REC1b, section 5; judge 641 SF1).
`complete` only when the school step is `ok` for a reason other than its switch being off or the day not being a
session, and the session's 15:00 decisions file is sealed and reads with its SHA-256 checked. Every other state is
`unavailable` with the step's status and reason code; an `ok` status alone never makes the source complete."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Protocol

from ..books.version_registry import SCHOOL_BOOK_PREFIX
from ..constants import SCHOOL_STEP, STEP_OK
from ..school.constants import SLOT_1500, Outcome, RecordKind
from ..school.contracts.records import DecisionRecord
from ..school.contracts.seal import Seal, StaleSeal
from .constants import CandidateSourceName, SourceState
from .contracts import CandidateSource
from .ports import CandidateSourcePort, InputFailed, SeenDecision, SourceReading, open_run_log
from .refs import RecordRef

NOT_RUN = frozenset({"school:OFF", "school:NOT_A_SESSION"})  # `ok`, yet the school ran nothing (judge 641 SF1)
STATUS = "{status}, {reason}"  # criterion 10: (<status>, <reason code>)
MISSING = "missing, the school step is not in the run log"
NO_SEAL = "the school step ran but no decisions file is sealed for {day}"


class SealedDecisions(Protocol):
    """The dashcam's sealed 15:00 decisions of a session: `DriveDashcamStore`'s own `find` and `read`."""

    def find(self, session: date, slot: str, kind: RecordKind) -> Seal | None: ...

    def read(self, seal: Seal) -> tuple: ...


class SchoolSource(CandidateSourcePort):
    name = CandidateSourceName.SCHOOL

    def __init__(self, root: Path, dashcam: SealedDecisions):
        self.root, self.dashcam = root, dashcam

    def read(self, day: date) -> SourceReading:
        log = open_run_log(self.root, day)
        if not log.done(SCHOOL_STEP):
            return _unavailable(MISSING)
        result = log.result(SCHOOL_STEP)
        status, reason = result.get("status", ""), result.get("reason", "")
        if status != STEP_OK or reason in NOT_RUN:
            return _unavailable(STATUS.format(status=status, reason=reason))
        seal = self.dashcam.find(day, SLOT_1500, RecordKind.DECISIONS)
        if seal is None:
            raise InputFailed(NO_SEAL.format(day=day))
        try:
            records = self.dashcam.read(seal)  # checks the file's SHA-256 against the seal
        except (StaleSeal, ValueError, OSError) as damaged:  # a damaged or unreadable seal, never fewer decisions
            raise InputFailed(f"{seal.path}: {type(damaged).__name__}") from None
        decisions = tuple(_seen(seal, r) for r in records if isinstance(r, DecisionRecord))
        return SourceReading(CandidateSource(self.name, SourceState.COMPLETE, None), decisions,
                             (RecordRef(seal.path, seal.sha256),))  # fmt: skip


def _seen(seal: Seal, record: DecisionRecord) -> SeenDecision:
    """One road's decision of a driver: the sealed file, with the road after `#` so each decision has its own key."""
    version = SCHOOL_BOOK_PREFIX + record.decision.driver_id
    traded = record.decision.outcome is Outcome.TRADE  # a ticket is a measurement, never a paper trade
    return SeenDecision(version, RecordRef(f"{seal.path}#{record.road}", seal.sha256), traded)


def _unavailable(status: str) -> SourceReading:
    return SourceReading(CandidateSource(CandidateSourceName.SCHOOL, SourceState.UNAVAILABLE, status), (), ())
