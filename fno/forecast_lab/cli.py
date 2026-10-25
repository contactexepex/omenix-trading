"""`python -m fno lab open|close [--day D]` (stories FL1-1 and FL1-1d): the morning edition (today's forecast, before
09:15) and the evening edition (was today's forecast right?) to #fno-forecast, each run by its own owner routine.
Exit 0 when the report was posted or there was nothing to post (not live, not a regular session, an already-posted
rerun); exit 1 when it was not posted (the routine notes it; the run alerts what it must itself).
`python -m fno lab preview --edition morning|evening --day D` (FL1-1f): the owner's preview, posted once and labelled
a dry run, writing nothing (`preview.py`); exit 1 unless posted.
`python -m fno lab channels`: criterion 7's read-only membership check of the lab's two channels, a go-live check;
exit 1 unless the bot is a member of both."""

from __future__ import annotations

import os
from datetime import date, time

NO_TOKEN = "lab channels: FNO_SLACK_BOT_TOKEN is not set; membership not checked"
NO_EDITION = "lab preview: say which edition (--edition morning or --edition evening)"
PREVIEW_AT = {"morning": time(8, 50), "evening": time(20, 5)}  # each edition's own posting time


def add_lab_parser(subparsers) -> None:
    p = subparsers.add_parser("lab", help="FL1: the forecast lab's morning and evening reports; channel membership")
    p.add_argument("action", choices=("open", "close", "release-check", "channels", "preview"))
    p.add_argument("--day", type=date.fromisoformat, default=None)
    p.add_argument("--edition", choices=("morning", "evening"), default=None, help="preview only")
    p.set_defaults(func=cmd_lab)


def cmd_lab(args, out=print, env=os.environ) -> int:
    if args.action == "channels":
        return _channels(out, env)
    if args.action == "release-check":
        return _release_check(args.day, out)
    if args.action == "preview":
        return _preview(args.edition, args.day, out)
    return _edition(args.action, args.day, out)


def _release_check(day: date | None, out) -> int:
    """FL1-1d-2: when NSE's evening files were out (read-only; logs only); never fails the routine."""
    from ..models import now_ist
    from .wiring import build_release_checks

    for line in build_release_checks().run(day or now_ist().date()):
        out(line)
    return 0


def _edition(action: str, day: date | None, out) -> int:
    from ..composition import build_alert_sender
    from ..models import now_ist
    from .constants import EVENING, MORNING
    from .edition_run import guarded
    from .wiring import build_edition

    edition = MORNING if action == "open" else EVENING
    result = guarded(edition, day or now_ist().date(), lambda: build_edition(edition), build_alert_sender())
    for line in result.lines:
        out(line)
    return 1 if result.failed else 0


def _preview(edition: str | None, day: date | None, out) -> int:
    from datetime import datetime

    from ..models import IST, now_ist
    from .wiring import build_preview

    if edition is None:
        out(NO_EDITION)
        return 1
    day = day or now_ist().date()
    at = PREVIEW_AT[edition]
    lines, posted = build_preview(edition).run(edition, day, datetime.combine(day, at, IST))
    for line in lines:
        out(line)
    return 0 if posted else 1


def _channels(out, env) -> int:
    import requests

    from ..constants import ENV_FNO_SLACK_BOT_TOKEN
    from .membership import check_membership

    token = env.get(ENV_FNO_SLACK_BOT_TOKEN)
    if not token:
        out(NO_TOKEN)
        return 1
    lines, every = check_membership(requests.Session(), token)
    for line in lines:
        out(line)
    return 0 if every else 1
