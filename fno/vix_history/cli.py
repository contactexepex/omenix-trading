"""`python -m fno vix-history <fill|sweep|check|verify>` (story A15; Drive since O9b).

- fill: archives the missing month files from NSE to the owner's Drive (with manifest rows), extends the table from
  them, then writes the checks. Resumable: run it again and only missing months are fetched.
- sweep: reads every month again from NSE and keeps a changed one as an A11 revision, named day by day.
- check: rewrites the checks from the committed table (no network).
- verify: recomputes the table from the month files in Drive and lists every difference (read-only).
The table and its checks live in Drive with receipts (O9b): commit `receipts/` and `research/data/manifests/` after a
run, as the rows are evidence only once their receipts are committed.
"""

from __future__ import annotations

from datetime import date, datetime

import requests

from ..models import now_ist
from ..research_data.calendar import CalendarError
from ..storage.owner_token import DriveSignInRefused
from ..storage.raw_source import RawSourceUnavailable
from ..storage.raw_store import RawFileConflict
from .source import NseVixHistorySource, last_complete_month, months_between
from .table import VixTableConflict

MONTH_FORMAT = "%Y-%m"
RESUME = "Nothing more was done; run the same command again (only missing months are fetched)."
STOPPING_FAILURES = (
    RawSourceUnavailable,
    requests.RequestException,  # Drive's network errors (NSE's failures arrive as RawSourceUnavailable, A9b)
    DriveSignInRefused,
    RawFileConflict,
    RuntimeError,  # Drive settings missing
    CalendarError,
    OSError,  # a missing calendar, closes or table file
)
COMMIT_REMINDER = "commit receipts/ and research/data/manifests/ (rows are evidence once their receipts are committed)"


def _month(text: str) -> date:
    return datetime.strptime(text, MONTH_FORMAT).date()


def add_vix_history_parser(subparsers) -> None:
    vix = subparsers.add_parser("vix-history", help="India VIX daily history from NSE (story A15)")
    vix.add_argument("action", choices=("fill", "sweep", "check", "verify"))
    vix.add_argument("--from", dest="start", type=_month, default=None, help="YYYY-MM (default: NSE's first month)")
    vix.add_argument("--to", dest="end", type=_month, default=None, help="YYYY-MM (default: the last ended month)")
    vix.set_defaults(func=cmd_vix_history)


def cmd_vix_history(args) -> int:
    """Every action; a Drive, network or setup failure stops it with a named line and exit 1, never a traceback."""
    action = {"fill": _fill, "sweep": _sweep, "check": _check, "verify": _verify}[args.action]
    try:
        return action(args)
    except STOPPING_FAILURES as exc:
        print(f"STOPPED ({type(exc).__name__}): {exc}. {RESUME}")
        return 1


def months_to_fetch(start: date | None, end: date | None, today: date) -> list[date]:
    """The months asked for, never one still running on `today` (its file would grow after it was archived)."""
    last_ended = last_complete_month(today)
    first = max(start or NseVixHistorySource.first_day, NseVixHistorySource.first_day)  # NSE serves nothing earlier
    return months_between(first, min(end or last_ended, last_ended))


def _fill(args) -> int:
    from .wiring import build_vix_librarian, build_vix_raw_area, build_vix_table, build_vix_table_builder

    raw, months = build_vix_raw_area(), months_to_fetch(args.start, args.end, now_ist().date())
    if not months:
        print("no ended month in the range asked for: nothing to do")
        return 1
    report = build_vix_librarian(raw).fill(months)
    print("\n".join(report.lines()))
    every_month = months_between(NseVixHistorySource.first_day, months[-1]) if months else []
    try:
        extension = build_vix_table_builder(raw).extend(every_month)
    except VixTableConflict as exc:
        print(f"table REFUSED (nothing rewritten): {exc}")
        return 1
    print("\n".join(extension.lines(build_vix_table())))
    _check(args)
    print(COMMIT_REMINDER)
    return 0 if report.complete and not extension.stopped_at else 1


def _sweep(args) -> int:
    from .wiring import build_vix_revision_sweep

    report = build_vix_revision_sweep().sweep(months_to_fetch(args.start, args.end, now_ist().date()))
    print("\n".join(report.lines()))
    print(COMMIT_REMINDER)
    return 0 if not (report.unanswered or report.invalid or report.not_archived or report.stopped) else 1


def _check(args) -> int:
    from .wiring import build_vix_checks, build_vix_table

    print("\n".join(build_vix_checks().write(build_vix_table().rows())))
    return 0


def _verify(args) -> int:
    from .wiring import build_vix_raw_area, build_vix_table, build_vix_verifier

    rows = build_vix_table().rows()
    if not rows:
        print("India VIX table is empty: nothing to verify")
        return 1
    problems = build_vix_verifier(build_vix_raw_area()).problems(rows)
    print("\n".join(problems) or f"India VIX table: all {len(rows)} days equal their archived month files")
    return 1 if problems else 0
