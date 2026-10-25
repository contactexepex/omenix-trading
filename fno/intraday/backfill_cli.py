"""`python -m fno intraday backfill | backfill-verify` (story A16b): Groww's 15-minute NIFTY candles from 2020 into a
candle-close realised variance per session, labelled back-filled. Read-only towards Groww; never places, modifies or
cancels orders. Exit 0 when every requested session has a row (or every row verifies); 1 otherwise."""

from __future__ import annotations

from datetime import date, time, timedelta
from pathlib import Path

from ..models import now_ist
from ..research_data.calendar import CalendarError
from .dry_run import inside_repository

BACKFILL, VERIFY = "backfill", "backfill-verify"
COMMANDS = (BACKFILL, VERIFY)
SESSION_SETTLED = time(21, 0)  # IST: NSE's index-close file, needed for the check, is archived by then (A13)
INSIDE_REPOSITORY = "a dry-run folder must be outside the repository (raw candles never go into it): {folder}"
STOPPED = "candle back-fill stopped ({reason}); what it wrote stays, run it again"
VERIFIED = "every candle-close row equals its Drive copies"


def add_backfill_parsers(actions) -> None:
    backfill = actions.add_parser(BACKFILL, help="Groww's 15-minute candles from 2020 into a back-filled RV (A16b)")
    backfill.add_argument("--from", dest="start", type=date.fromisoformat, help="YYYY-MM-DD (default 2020-01-01)")
    backfill.add_argument("--to", dest="end", type=date.fromisoformat, help="YYYY-MM-DD (default: latest finished)")
    backfill.add_argument("--dry-run", metavar="FOLDER", type=Path, help="live reads; files only under FOLDER")
    actions.add_parser(VERIFY, help="recompute every candle-close row from its Drive copies (read-only)")


def cmd_backfill(args) -> int:
    from ..config import load_app_config
    from .backfill import SERIES_START

    folder = getattr(args, "dry_run", None)
    if folder is not None and inside_repository(folder):
        print(INSIDE_REPOSITORY.format(folder=folder))
        return 1
    try:
        cfg = load_app_config(args.config)
        if args.intraday_cmd == VERIFY:
            return _verify()
        return _backfill(cfg, args.start or SERIES_START, args.end or latest_finished(now_ist()), folder)
    except CalendarError as error:
        print(f"candle back-fill stopped, nothing more written: {error}")
        return 1
    except Exception as error:  # the class name only: an exception's text could carry a credential
        print(STOPPED.format(reason=type(error).__name__))
        return 1


def latest_finished(now) -> date:
    """Today once NSE's file for it is out (21:00 IST), else yesterday; the run keeps only recorded sessions."""
    return now.date() if now.time() >= SESSION_SETTLED else now.date() - timedelta(days=1)


def _backfill(cfg: dict, start: date, end: date, folder: Path | None) -> int:
    from .backfill_report import report_lines
    from .backfill_wiring import build_candle_backfill, build_deferral_log

    backfill = build_candle_backfill(cfg, folder)
    report = backfill.run(start, end)
    wanted = {d.isoformat() for d in report.sessions}
    rows = [r for r in backfill.table.rows() if r["session"] in wanted]
    print("\n".join(report_lines(report, rows, build_deferral_log(folder).counts())))
    return 0 if report.complete and len(rows) == len(wanted) else 1


def _verify() -> int:
    from .backfill_wiring import build_candle_verifier

    problems = build_candle_verifier().problems()
    print("\n".join(problems) or VERIFIED)
    return 1 if problems else 0
