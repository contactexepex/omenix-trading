"""Where a candidate's outcome is found (story REC1c, text amendment item 3): a school candidate's `OutcomeRecord` in
the dashcam's sealed `outcomes` files from its session to the check's day, matched on the sealed decision file's
SHA-256, the driver and the road, corrections resolved to one live record (judge 658 S2). A desk candidate that traded
has no outcome reader yet (none can exist before a desk version reaches `paper`): it fails loudly, never a guess."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import date

from ..books.version_registry import SCHOOL_BOOK_PREFIX
from ..school.constants import SLOT_1500, Outcome, RecordKind
from ..school.contracts.records import DecisionRecord, OutcomeRecord
from ..school.contracts.seal import StaleSeal
from ..school.instructor.contracts import record_sha256
from .check import FoundOutcome, OutcomeLookup
from .constants import CandidateSourceName
from .contracts import Candidate, source_of
from .ports import DataDisagrees, InputFailed
from .school_source import SealedDecisions

ROAD_MARK = "#"
NO_DECISION = "{key}: its sealed decisions file is not the one the recommendation listed"
ORPHAN = "{key}: an outcome corrects a record that is not on file"
TWO_LIVE = "{key}: {count} live outcomes for one candidate"
DESK_NOT_BUILT = "{version}: a desk candidate traded, and the desk's outcome reader is not built (REC1c)"


class SealedOutcomes(OutcomeLookup):
    def __init__(self, dashcam: SealedDecisions, sessions: Callable[[date, date], Iterable[date]]):
        """`sessions(a, b)`: the NSE sessions from a to b, both included."""
        self.dashcam, self.sessions = dashcam, sessions
        self._read: dict[date, tuple[OutcomeRecord, ...]] = {}  # one read per session file per run

    def outcome(self, candidate: Candidate, session: date, until: date) -> FoundOutcome | None:
        if source_of(candidate.version) is not CandidateSourceName.SCHOOL:
            if candidate.traded:
                raise InputFailed(DESK_NOT_BUILT.format(version=candidate.version))
            return None
        _, _, road = candidate.decision.path.partition(ROAD_MARK)
        driver = candidate.version.removeprefix(SCHOOL_BOOK_PREFIX)
        found = [r for day in self.sessions(session, until) for r in self._outcomes(day)
                 if (r.decision_sha256, r.driver_id, r.road) == (candidate.decision.sha256, driver, road)]  # fmt: skip
        live = _live(found, candidate.decision.path)
        return None if live is None else FoundOutcome(live.net, live.is_ticket)

    def ticket(self, candidate: Candidate, session: date) -> bool:
        if source_of(candidate.version) is not CandidateSourceName.SCHOOL:
            return False
        _, _, road = candidate.decision.path.partition(ROAD_MARK)
        driver = candidate.version.removeprefix(SCHOOL_BOOK_PREFIX)
        seal = self.dashcam.find(session, SLOT_1500, RecordKind.DECISIONS)
        records = self._read_seal(seal) if seal is not None and seal.sha256 == candidate.decision.sha256 else None
        if records is None:
            raise InputFailed(NO_DECISION.format(key=candidate.decision.path))
        return any(isinstance(r, DecisionRecord) and (r.decision.driver_id, r.road) == (driver, road)
                   and r.decision.outcome is Outcome.TICKET for r in records)  # fmt: skip

    def _outcomes(self, day: date) -> tuple[OutcomeRecord, ...]:
        if day not in self._read:
            seal = self.dashcam.find(day, SLOT_1500, RecordKind.OUTCOMES)
            records = self._read_seal(seal) if seal is not None else ()
            self._read[day] = tuple(r for r in records if isinstance(r, OutcomeRecord))
        return self._read[day]

    def _read_seal(self, seal) -> tuple:
        try:
            return self.dashcam.read(seal)
        except (StaleSeal, ValueError, OSError) as damaged:  # never fewer records: the whole check fails
            raise InputFailed(f"{seal.path}: {type(damaged).__name__}") from None


def _live(found: list[OutcomeRecord], key: str) -> OutcomeRecord | None:
    """Corrections resolved first (judge 658 S2): a record a later one names in `corrects` drops out. One live record
    is the outcome; none, open; two or more, or a correction of a record that is not there, a failed check."""
    identities = {record_sha256(r) for r in found}
    replaced = {r.corrects for r in found if r.corrects}
    if replaced - identities:
        raise DataDisagrees(ORPHAN.format(key=key))
    live = [r for r in found if record_sha256(r) not in replaced]
    if len(live) > 1:
        raise DataDisagrees(TWO_LIVE.format(key=key, count=len(live)))
    return live[0] if live else None
