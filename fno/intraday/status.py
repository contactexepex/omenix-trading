"""Whether a snapshot is good for its mark (story A16). One function decides it, used both when a snapshot is taken
(the ledger's status) and when a session's realised variance is computed from the stored snapshots, so the two can
never disagree.

The index level is usable only when taken on time (sent at or after the mark, answered within 120 s) with the
source's own time at most 120 s older than our receive time (design 5.2). A level equal to the previous mark's is only
flagged (`index_repeated`, judge 108): NIFTY ticks in 0.05 steps and calm intervals exist, so voiding them would bias
the realised variance upward; a frozen feed shows up as an old source time instead."""

from __future__ import annotations

from dataclasses import dataclass

from .document import SnapshotDocument
from .slots import ON_TIME_SECONDS, window_end

GOOD, MISSED, LATE, STALE, FAILED, INCOMPLETE = "good", "missed", "late", "stale", "failed", "incomplete"
INDEX_FAILED = "index_failed"
INDEX_LATE = "index_late"
INDEX_TIME_MISSING = "index_time_missing"
INDEX_TIME_OLD = "index_time_old"
INDEX_REPEATED = "index_repeated"  # a flag on the row, never a status
SOURCE_AHEAD_OF_HOST = "source_ahead_of_host"
CONTRACTS_MISSING = "contracts_missing"
CHAIN_EMPTY = "chain_empty"
CHAINS_EXPECTED = 2  # the nearest listed expiry and the nearest monthly (or the next listed)
QUOTE_PREFIX, QUOTES_FAILED = "quote ", "quotes_failed:{count}"
AHEAD_TOLERANCE_SECONDS = 5  # the source's time after our receive time by more than this: one clock is wrong
INDEX_STATUS = {
    INDEX_FAILED: FAILED, INDEX_LATE: LATE, INDEX_TIME_MISSING: STALE, INDEX_TIME_OLD: STALE,
}  # fmt: skip


@dataclass(frozen=True)
class IndexCheck:
    level: float | None  # the usable level, None when the problem below makes it unusable
    problem: str  # empty when usable


@dataclass(frozen=True)
class SlotVerdict:
    status: str
    failures: tuple[str, ...]  # named reasons: the index problem, missing contracts, failed steps, clock notes


def index_check(doc: SnapshotDocument) -> IndexCheck:
    """The index level if usable for the realised variance, else why not."""
    call = doc.index
    if call.failure or not doc.index_level or doc.index_level < 0 or call.response_received_at is None:
        return IndexCheck(None, INDEX_FAILED)
    if call.request_sent_at < doc.mark or call.response_received_at > window_end(doc.mark):
        return IndexCheck(None, INDEX_LATE)
    if doc.index_source_time is None:
        return IndexCheck(None, INDEX_TIME_MISSING)
    if (call.response_received_at - doc.index_source_time).total_seconds() > ON_TIME_SECONDS:
        return IndexCheck(None, INDEX_TIME_OLD)
    return IndexCheck(doc.index_level, "")


def verdict(doc: SnapshotDocument, previous_level: float | None) -> SlotVerdict:
    """The slot's status and every named reason behind it. Failed contract quotes are counted, not listed one by one,
    so a ledger row and an alert stay readable; the document keeps every name."""
    check = index_check(doc)
    notes = [check.problem] if check.problem else []
    if _chain_empty(doc):
        notes.append(CHAIN_EMPTY)
    if doc.recorded_contracts < doc.expected_contracts:
        notes.append(CONTRACTS_MISSING)
    named = [f for f in doc.failures if not f.startswith(QUOTE_PREFIX)]
    quotes_failed = len(doc.failures) - len(named)
    notes += [f for f in named if f not in notes]
    notes += [QUOTES_FAILED.format(count=quotes_failed)] if quotes_failed else []
    status = INDEX_STATUS[check.problem] if check.problem else (INCOMPLETE if notes else GOOD)
    flags = [SOURCE_AHEAD_OF_HOST] if _source_ahead(doc) else []  # a clock note: recorded, not a status
    flags += [INDEX_REPEATED] if check.level is not None and check.level == previous_level else []
    return SlotVerdict(status, tuple(notes + flags + doc.notes))


def _chain_empty(doc: SnapshotDocument) -> bool:
    """Fewer chains than planned, or a chain that failed or had no contract in the band: never good."""
    answered = [c for c in doc.chains if not c.failure and c.meta.get("contracts", 0) > 0]
    return len(answered) < CHAINS_EXPECTED


def _source_ahead(doc: SnapshotDocument) -> bool:
    received, source_time = doc.index.response_received_at, doc.index_source_time
    return bool(received and source_time and (source_time - received).total_seconds() > AHEAD_TOLERANCE_SECONDS)
