"""One named line in the job's log when any command stops on NSE's calendar (story O8c, response 239 item 4; judge 246).

Every job that asks the calendar about a day it does not cover raises `CalendarError`; most let it escape as a
traceback. `fno/cli.py` sends that error here once, for every command: one line naming the command and the calendar's
own words (the day and the year to add), exit 1. It is printed, not posted: the gap is announced in #fno-desk already
(O8b's once-only warning 45 days ahead; from the first uncovered day, the daily health check's "FAILED: CalendarError"),
and each workflow's own failure line points to this log. Posting here too would give several lines per run for one stop
(judge 246)."""

from __future__ import annotations

import sys
from collections.abc import Sequence

CALENDAR_STOP = "Omenix F&O `{command}` stopped: {reason}"


def command_name(argv: Sequence[str] | None) -> str:
    """The command and its action, without options (`pipeline index-closes`, `data-librarian index-close`)."""
    tokens = list(sys.argv[1:] if argv is None else argv)
    words = [token for token in tokens[:2] if not token.startswith("-")]
    return " ".join(words) or "fno"


def calendar_stop(command: str, error: Exception, out=print) -> int:
    out(CALENDAR_STOP.format(command=command, reason=error))
    return 1
