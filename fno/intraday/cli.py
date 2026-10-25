"""Commands of the 15-minute recorder (story A16): `python -m fno intraday snapshot | run | rv | heartbeat-check`.
Research data only: never places, modifies or cancels orders. Exit 0 for a good snapshot, a mark already recorded,
no mark now or a day that is not a session; 1 otherwise."""

from __future__ import annotations

from datetime import date, datetime, time
from pathlib import Path

from ..alerts.output import announce
from ..models import IST, now_ist
from ..research_data.calendar import CalendarError
from .backfill_cli import COMMANDS as BACKFILL_COMMANDS
from .backfill_cli import add_backfill_parsers, cmd_backfill
from .cover import covered_until
from .dry_run import inside_repository
from .feed_cli import FEED_PROBE, add_feed_probe_parser, cmd_feed_probe
from .recorder import GOOD_OUTCOMES, SettleRefused, SlotOutcome

DEFAULT_UNTIL = "15:35"
CALENDAR_STOP = "15-minute recorder stopped, nothing recorded: {error} ({file})"
STOPPED = (
    "Action: check the 15-minute recorder (story A16): it stopped with {reason} before or while taking a mark; "
    "missed marks stay gaps"
)
INSIDE_REPOSITORY = "a dry-run folder must be outside the repository (raw quotes never go into it): {folder}"


def add_intraday_parser(subparsers) -> None:
    intraday = subparsers.add_parser("intraday", help="15-minute NIFTY snapshots from Groww (story A16; never orders)")
    actions = intraday.add_subparsers(dest="intraday_cmd", required=True)
    snapshot = actions.add_parser("snapshot", help="take the next mark (waits at most 15 minutes for it)")
    run = actions.add_parser("run", help="the session loop: every mark up to --until (IST)")
    run.add_argument("--until", type=_clock_time, default=_clock_time(DEFAULT_UNTIL), help="HH:MM IST")
    for action in (snapshot, run):
        action.add_argument("--dry-run", metavar="FOLDER", type=Path, help="live reads; files only under FOLDER")
    rv = actions.add_parser("rv", help="settle a finished session: missed rows and its realised variance")
    rv.add_argument("--day", type=date.fromisoformat, help="YYYY-MM-DD (default: the latest finished session)")
    actions.add_parser("heartbeat-check", help="alert when the recorder has been silent for 30 minutes")
    add_backfill_parsers(actions)  # story A16b
    add_feed_probe_parser(actions)  # story A16h
    intraday.set_defaults(func=cmd_intraday)


def cmd_intraday(args) -> int:
    from ..alerts.sender import NoAlertSender
    from ..composition import build_alert_sender
    from ..config import load_app_config
    from ..daily.alerts import ReportedAlerts
    from ..storage.wiring import build_session_calendar
    from .wiring import DRY_RUN_ALERTS, build_heartbeat, build_intraday_recorder

    if args.intraday_cmd in BACKFILL_COMMANDS:
        return cmd_backfill(args)
    if args.intraday_cmd == FEED_PROBE:
        return cmd_feed_probe(args)
    if args.intraday_cmd == "heartbeat-check":
        alerts = ReportedAlerts(build_alert_sender())  # an unsent alert is printed with its text (O2)
        return heartbeat_check(build_heartbeat(), build_session_calendar(), alerts, now_ist())
    folder = getattr(args, "dry_run", None)
    if folder is not None and inside_repository(folder):
        print(INSIDE_REPOSITORY.format(folder=folder))
        return 1
    alerts = ReportedAlerts(NoAlertSender(DRY_RUN_ALERTS) if folder is not None else build_alert_sender())
    try:
        recorder = build_intraday_recorder(load_app_config(args.config), folder)
        if args.intraday_cmd == "rv":
            print("\n".join(recorder.settle_day(args.day)))
            return 0
        outcomes = [recorder.snapshot()] if args.intraday_cmd == "snapshot" else recorder.run(covered_until(args.until))
    except CalendarError as error:
        return _calendar_stop(error, alerts)
    except SettleRefused as error:
        print(f"rv refused: {error}")
        return 1
    except Exception as error:  # the class name only: an exception's text could carry a credential
        message = STOPPED.format(reason=type(error).__name__)
        print(message)
        announce(alerts, message)
        return 1
    return report(outcomes)


def report(outcomes: list[SlotOutcome]) -> int:
    for outcome in outcomes:
        print("\n".join([outcome.summary(), *outcome.lines]))
    return 0 if all(o.status in GOOD_OUTCOMES for o in outcomes) else 1


def heartbeat_check(heartbeat, calendar, alerts, now: datetime) -> int:
    from ..quotes.recorder import RECORDED_SESSION_KINDS
    from .heartbeat import SILENT, SILENT_ALERT, heartbeat_state

    try:
        recorded = calendar.session_kind(now.astimezone(IST).date()) in RECORDED_SESSION_KINDS
    except CalendarError as error:
        return _calendar_stop(error, alerts)
    state = heartbeat_state(heartbeat.read(), now, recorded)
    print(state.line)
    if state.status != SILENT:
        return 0
    announce(alerts, SILENT_ALERT.format(detail=state.line))
    return 1


def _calendar_stop(error: CalendarError, alerts) -> int:
    from ..config import ROOT
    from ..storage.wiring import CALENDAR_FILE

    message = CALENDAR_STOP.format(error=error, file=CALENDAR_FILE.relative_to(ROOT).as_posix())
    print(message)
    announce(alerts, message)
    return 1


def _clock_time(text: str) -> time:
    return datetime.strptime(text, "%H:%M").time()
