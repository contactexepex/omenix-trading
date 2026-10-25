"""`python -m fno records ...` (story DR1):

- `certify <dataset> [--day D | --since N] [--level provisional|certified] [--commit]`: checks every version of the
  session and writes the record (local unless `--commit`, which pushes `receipts/records/` to main); `--since N`
  certifies every NSE session of the last N days, so a session missed on one run is caught up on the next (one line
  each; a session already recorded says so). The window ends at the day (`--day`, default today) for a provisional
  record and at the session before it for a certified one: a session's certified record is due only once NSE's
  official file is out, the next morning (judge 546). Exit 1 when any session is not recorded.
- `read <dataset> [--day D] [--level ...]`: prints the as-seen pointer of what a reader would get (never a value).
  Exit 1 when no record serves the need."""

from __future__ import annotations

from .constants import ALERT, CERTIFIED, LEVELS, PROVISIONAL, SEEN_LINE


def add_records_parser(subparsers) -> None:
    from .wiring import DATASETS

    records = subparsers.add_parser("records", help="staging, certification and the as-seen record (DR1)")
    actions = records.add_subparsers(dest="records_action", required=True)
    for name, func, text in (("certify", cmd_certify, "certify a session"), ("read", cmd_read, "read a record")):
        action = actions.add_parser(name, help=text)
        action.add_argument("dataset", choices=DATASETS)
        action.add_argument("--day", help="the session, YYYY-MM-DD (default: today, IST)")
        action.add_argument("--level", choices=LEVELS, default=PROVISIONAL)
        if name == "certify":
            action.add_argument("--since", type=int, help="every session of the N days before --day (catch-up); "
                                "certified: up to the previous session, provisional: up to --day")  # fmt: skip
            action.add_argument("--commit", action="store_true", help="commit and push the record to main")
        action.set_defaults(func=func)


def _session(args) -> str:
    from ..models import now_ist

    return args.day or now_ist().date().isoformat()


def cmd_certify(args, out=print, certifier=None, alerts=None, calendar=None) -> int:
    """A record not on origin's main, a conflict or an unreadable source also goes to #fno-desk, in one alert per run
    naming every session (judge 561's note: `--since 7` with a store down would otherwise alert seven times)."""
    from ..alerts.output import announce
    from .wiring import build_alerts, build_certifier

    certifier = certifier or build_certifier(args.dataset, args.commit)
    recorded, alerted = True, []
    for session in _sessions(args, calendar, certifier.rules.live_from):
        outcome = certifier.certify(session, args.level)
        out(outcome.line)
        if outcome.alert:
            alerted.append(outcome.line)
        recorded = recorded and outcome.recorded
    if alerted:
        announce(alerts or build_alerts(), ALERT.format(line="\n".join(alerted)))
    return 0 if recorded else 1


def _sessions(args, calendar, live_from) -> list[str]:
    if getattr(args, "since", None) is None:
        return [_session(args)]
    from datetime import date, timedelta

    from ..storage.wiring import build_session_calendar

    calendar = calendar or build_session_calendar()
    today = date.fromisoformat(_session(args))
    start = max(today - timedelta(days=args.since), live_from)
    end = today - timedelta(days=1) if args.level == CERTIFIED else today
    return [day.isoformat() for day in calendar.sessions(start, end)]


def cmd_read(args, out=print, reader=None) -> int:
    from .reader import NotRecorded
    from .wiring import build_record_reader

    reader = reader or build_record_reader()
    try:
        seen = reader.read(args.dataset, _session(args), args.level).as_seen
    except NotRecorded as refusal:
        out(str(refusal))
        return 1
    out(SEEN_LINE.format(dataset=seen.dataset, session=seen.session, level=seen.level, path=seen.path,
                         sha=seen.sha256[:12]))  # fmt: skip
    return 0
