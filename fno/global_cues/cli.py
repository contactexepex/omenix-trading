"""`python -m fno global-cues <fill|check|verify|adopt> [--cue NAME ...] [--from DATE] [--to DATE]` (story A17).

- fill: downloads each cue's files, archives them in the owner's Drive, extends the tables, rewrites the checks. The
  first run back-fills from each source's first date; later runs look back 31 days. Scheduled by
  .github/workflows/global-cues.yml (03:41, 04:41 and 14:11 IST).
- check: rewrites the checks from the tables (the public ones offline; with the Drive settings also the private
  ones, whose gaps are written to Drive).
- verify: recomputes every table row from the archived copy it names (read-only).
- adopt: takes a copy already in Drive's raw area into its cue's log and table, first seen at its own fetch time.
- preopen: the Asian index levels before 09:15 IST (story A17e part B), called by A22's pre-open routine.
Commit `research/data/global-cues/` and `research/data/manifests/global-cues/` after a run.
"""

from __future__ import annotations

from datetime import date

import requests

from ..models import now_ist
from ..research_data.calendar import CalendarError
from ..storage.owner_token import DriveSignInRefused

STOPPING_FAILURES = (
    requests.RequestException,  # Drive's network errors (a publisher's are named per cue by the job)
    DriveSignInRefused,
    RuntimeError,  # Drive settings missing
    CalendarError,
    OSError,  # a missing calendar or table file
    KeyError,  # a table file missing a column
    ValueError,  # a table cell that is not a number or a date
)


def add_global_cues_parser(subparsers) -> None:
    from .wiring import SOURCES

    cues = subparsers.add_parser(
        "global-cues", help="US closes, world indexes, US 10-year, Brent and USD/INR (A17, A17e)"
    )
    cues.add_argument("action", choices=("fill", "check", "verify", "adopt", "preopen"))
    cues.add_argument("--cue", action="append", choices=[s.cue for s in SOURCES], help="one cue (repeatable)")
    cues.add_argument("--from", dest="start", type=date.fromisoformat, default=None, help="YYYY-MM-DD")
    cues.add_argument("--to", dest="end", type=date.fromisoformat, default=None, help="YYYY-MM-DD (default: today)")
    cues.add_argument("--copy", help="adopt: a copy's path in Drive's raw area, e.g. cboe/indices/spx-history/...")
    cues.set_defaults(func=cmd_global_cues)


def cmd_global_cues(args) -> int:
    """Every action; a Drive or setup failure stops it with one named line and exit 1, never a traceback."""
    action = {"fill": _fill, "check": _check, "verify": _verify, "adopt": _adopt, "preopen": _preopen}[args.action]
    try:
        return action(args)
    except STOPPING_FAILURES as exc:
        print(f"STOPPED ({type(exc).__name__}): {exc}. Run the same command again.")
        return 1


def _fill(args) -> int:
    from .wiring import build_behind_check, build_job, sources_named

    end = args.end or now_ist().date()
    if args.start and args.start > end:
        print(f"--from {args.start} is after --to {end}: nothing asked for")
        return 1
    lines, ok = build_job().run(sources_named(args.cue), args.start, end)
    behind_lines, on_time = build_behind_check().run(now_ist().date())
    print("\n".join(lines + behind_lines))
    return 0 if ok and on_time else 1


def _check(args) -> int:
    from .wiring import build_checks

    print("\n".join(build_checks().write()))
    return 0


def _verify(args) -> int:
    from .wiring import build_tables, build_verifier, sources_named

    verifier, tables = build_verifier(), build_tables()
    sources = sources_named(args.cue)
    problems = [f"{s.cue}: the table has no rows, nothing verified" for s in sources if not tables[s.cue].rows()]
    problems += [p for s in sources for p in verifier.problems(s, tables[s.cue].rows())]
    print("\n".join(problems) or "every cue row equals the archived copy it names")
    return 1 if problems else 0


def _preopen(args) -> int:
    from .preopen_cli import cmd_preopen

    return cmd_preopen()


def _adopt(args) -> int:
    """One copy already in Drive (owner: keep and use the four US-index files) into its cue's log and table."""
    from .wiring import build_job, sources_named

    sources = sources_named(args.cue)
    if len(sources) != 1 or not args.copy:
        print("adopt needs exactly one --cue and a --copy path")
        return 1
    source = sources[0]
    lines, ok = build_job().adopt(
        source, args.copy, args.start or source.first_value_date, args.end or now_ist().date()
    )
    print("\n".join(lines))
    return 0 if ok else 1
