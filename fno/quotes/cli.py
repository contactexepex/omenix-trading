"""Commands for the 3 pm quote recorder: `python -m fno quotes record` and `python -m fno quotes report`."""

from __future__ import annotations

import json
from collections.abc import Callable
from functools import partial

from ..alerts.output import announce
from ..alerts.sender import AlertSender
from ..research_data.calendar import CalendarError
from .recorder import NO_SAME_DAY_TRADES, RAW_FILE_NOT_SAVED, QuoteSnapshotRecorder, RecordResult

CALENDAR_STOP = "3 pm quote recorder stopped, nothing recorded: {error} ({file})"
CROSS_CHECK_ALERT = (
    "3 pm quote recorder: {reason} ({snapshot_id}, kept with complete=False). Check NSE for an unlisted closure or a "
    "data outage; if NSE was closed, add the day to the calendar file with its circular."
)
MONTHLY_UNVERIFIED_ALERT = (
    "3 pm quote recorder: monthly contracts chosen by the last-listed-expiry rule, not verified against NSE's history "
    "({reason}; {snapshot_id}). Quotes were kept; check the contract choice later (meta.json monthly_check)."
)
RAW_FILE_ALERT = (
    "3 pm quote recorder: raw quote file NOT saved to Drive ({reason}; {snapshot_id}). The sidecar is kept, no raw "
    "quote went to the repository; an attempt in the 14:55-15:10 window is retried each minute. Fix: check the four "
    "FNO_GDRIVE_* settings (A9: run tools/gdrive_oauth_setup.py if the owner's consent expired)."
)
CONFIGURED, NSE_SOURCE = "configured", "nse"
GOOD_STATUSES = ("recorded", "already recorded", "not a trading day")
WINDOW_REFUSED = "3 pm quote recorder: nothing asked"
WINDOW_NSE = "--window is for the configured provider's capture only, not --source nse"


def add_quotes_parser(subparsers) -> None:
    quotes = subparsers.add_parser("quotes", help="record real 3 pm bid/ask quotes of NIFTY options (never orders)")
    actions = quotes.add_subparsers(dest="quotes_cmd", required=True)
    record = actions.add_parser("record", help="record today's snapshot in the 14:55-15:10 IST window")
    record.add_argument("--outside-window", action="store_true", help="testing only: one attempt now, never canonical")
    record.add_argument(
        "--source",
        choices=(CONFIGURED, NSE_SOURCE),
        default=CONFIGURED,
        help="nse: NSE's public option chain into its own dataset (story O6); default: quotes.provider",
    )
    record.add_argument("--window", help="a named window of config.yaml quotes.windows, in its own dataset (story A4e)")
    actions.add_parser("record-indices", help="BANKNIFTY, FINNIFTY and MIDCPNIFTY after NIFTY's push (15:01-15:13 IST)")
    actions.add_parser("compare", help="Groww's and NSE's canonical snapshots side by side, day by day (story O6)")
    actions.add_parser("report", help="median and 90th-percentile half-spread by distance from the money")
    quotes.set_defaults(func=cmd_quotes)


def cmd_quotes(args) -> int:
    from ..composition import build_alert_sender, build_nse_quote_recorder, build_quote_recorder
    from ..config import ROOT, load_app_config
    from ..daily.alerts import ReportedAlerts
    from ..storage.wiring import CALENDAR_FILE, QUOTES_FOLDER, build_quote_store
    from .report import canonical_snapshots, spread_report

    if args.quotes_cmd == "report":
        snapshots = canonical_snapshots(QUOTES_FOLDER, build_quote_store(QUOTES_FOLDER))  # Groww's only
        print(json.dumps(spread_report(snapshots), indent=1))
        return 0
    if args.quotes_cmd == "compare":
        from .compare import compare_lines

        print("\n".join(compare_lines(QUOTES_FOLDER, build_quote_store(QUOTES_FOLDER))))
        return 0
    calendar_file = CALENDAR_FILE.relative_to(ROOT).as_posix()
    alerts = ReportedAlerts(build_alert_sender())  # an unsent alert is printed with its text (O2)
    if args.quotes_cmd == "record-indices":
        from .index_wiring import build_index_quote_recorders
        from .indices_cli import record_indices

        build_indices = partial(build_index_quote_recorders, load_app_config(args.config))
        return record_indices(build_indices, alerts, calendar_file)
    if args.window:
        return _record_window(args, alerts, calendar_file)
    builder = build_nse_quote_recorder if args.source == NSE_SOURCE else build_quote_recorder
    build = partial(builder, load_app_config(args.config))
    return record_today(build, alerts, args.outside_window, calendar_file)


def _record_window(args, alerts: AlertSender, calendar_file: str) -> int:
    """A named window (story A4e): Groww's capture only; a bad or unknown window stops before anything is asked."""
    from ..config import ConfigError, load_app_config
    from .window import named_window
    from .window_wiring import build_window_quote_recorder

    cfg = load_app_config(args.config)
    try:
        if args.source == NSE_SOURCE:
            raise ConfigError(WINDOW_NSE)
        named_window(cfg, args.window)
    except ConfigError as error:
        print(f"{WINDOW_REFUSED}: {error}")
        return 1
    return record_today(partial(build_window_quote_recorder, cfg, args.window), alerts, args.outside_window,
                        calendar_file)  # fmt: skip


def record_today(
    build: Callable[[], QuoteSnapshotRecorder], alerts: AlertSender, outside_window: bool, calendar_file: str
) -> int:
    """Runs one day's recording, prints the result line and returns the exit code. A calendar that cannot answer for
    today (outside its years, or an invalid file) stops the run loudly. A session day with no same-day trade, and
    monthly contracts chosen without NSE's history, are alerted to #fno-desk; each alert's outcome line is printed
    ("alert NOT sent" without the Slack token)."""
    try:
        result = build().record(outside_window=outside_window)
    except CalendarError as error:
        message = CALENDAR_STOP.format(error=error, file=calendar_file)
        print(message)
        announce(alerts, message)
        return 1
    reason = "".join(f" - {text}" for text in (result.reason, result.raw_file_error) if text)
    print(f"{result.status}: {result.snapshot_id or '-'} ({result.rows} contracts, complete={result.complete}){reason}")
    if result.reason == NO_SAME_DAY_TRADES:
        announce(alerts, CROSS_CHECK_ALERT.format(reason=result.reason, snapshot_id=result.snapshot_id))
    if result.monthly_unverified:
        alert = MONTHLY_UNVERIFIED_ALERT.format(reason=result.monthly_unverified, snapshot_id=result.snapshot_id)
        announce(alerts, alert)
    if result.raw_file_error:
        error = f"{result.raw_file_error.removeprefix(f'{RAW_FILE_NOT_SAVED}: ')}: {result.raw_file_detail}"
        announce(alerts, RAW_FILE_ALERT.format(reason=error, snapshot_id=result.snapshot_id))  # Slack: private
    return exit_code(result, outside_window)


def exit_code(result: RecordResult, outside_window: bool) -> int:
    """0 for a complete recording, a rerun or a closed market; 1 otherwise. An incomplete outside-window test attempt
    is fine, unless it failed the calendar cross-check or its quote file was not saved."""
    if result.status not in GOOD_STATUSES or result.reason == NO_SAME_DAY_TRADES or result.raw_file_error:
        return 1
    return 0 if result.complete or result.status != "recorded" or outside_window else 1
