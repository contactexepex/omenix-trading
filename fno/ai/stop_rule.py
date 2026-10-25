"""The stop rule (owner's condition 1, 14 Oct 2026): two transcript breaches by one book within its last 20 session days
stop that book's fires until the prompt or design is fixed, which means a new registered version (breaches of an
older version do not count against the new one). The fire step asks this before each book. A protocol's own terms say
where its audits are (v2 the default); v4's session days are the calendar's, passed in by its firer (G11 round 2c),
because v4 has no v2 pack file per day."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from pathlib import Path

from .coverage import pack_days
from .run_terms import V2_TERMS, RunTerms
from .transcript_audit import BREACH, TranscriptAudits

WINDOW_SESSION_DAYS, BREACHES_TO_STOP = 20, 2
STOPPED = "stopped: {count} transcript breaches in {window} session days ({days}); register a fixed version"


def breached_days(root: Path, book: str, version: str, before: date, terms: RunTerms = V2_TERMS,
                  sessions: Sequence[date] | None = None) -> list[date]:  # fmt: skip
    """Days among the book's last 20 session days before `before` whose audit, under `version`, found a breach.
    `sessions`: the session days to count (default: v2's pack days)."""
    days = pack_days(root) if sessions is None else sorted(sessions)
    window = [d for d in days if d < before][-WINDOW_SESSION_DAYS:]
    audits = TranscriptAudits(root, terms)
    return [d for d in window if (a := audits.get(d, book)) and a.result == BREACH and a.version == version]


def stop_reason(root: Path, book: str, version: str, day: date, terms: RunTerms = V2_TERMS,
                sessions: Sequence[date] | None = None) -> str:  # fmt: skip
    """Why the book must not be fired on `day`, or '' when it may."""
    days = breached_days(root, book, version, day, terms, sessions)
    if len(days) < BREACHES_TO_STOP:
        return ""
    listed = ", ".join(d.isoformat() for d in days)
    return STOPPED.format(count=len(days), window=WINDOW_SESSION_DAYS, days=listed)
