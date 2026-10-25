"""`python -m fno flows table <dataset>` (story A23): enters every newly archived session of NSE's participant volume
or FII derivatives statistics in the flow-history table (write time, point-in-time dates, values), commits the
write-time log and the receipts, and posts one #fno-desk line naming any problem. Exit 1 on any problem."""

from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta

from ..models import today_local

SUMMARY = "flows table {name}: {entered} session(s) entered ({rewritten} rewritten), {waiting} waiting"
ALERT = "Omenix F&O flow history {name}: {count} problem(s): {first}; see {where}"
NOT_COMMITTED = " NOT committed"
SHOWN_IN_ALERT = 3
NSDL_FIRST_MONTH = date(2019, 1, 31)
NSDL_SUMMARY = (
    "nsdl-backfill: {saved} month(s) saved ({rows} rows, {empty} with no reporting date), {skipped} already done, "
    "{failed} failed"
)
NSDL_FAILED = "{month:%Y-%m} failed twice: {why}"
NSDL_ALERT = "Omenix F&O NSDL FPI back-fill: {count} month(s) failed twice: {months}; see {where}"


def add_flows_parser(subparsers) -> None:
    from .wiring import VALUES

    flows = subparsers.add_parser("flows", help="FII/DII flow history from 2019 (story A23)")
    actions = flows.add_subparsers(dest="flows_action", required=True)
    table = actions.add_parser("table", help="enter newly archived sessions in the flow-history table")
    table.add_argument("dataset", choices=sorted(VALUES))
    table.set_defaults(func=cmd_flows_table)
    nsdl = actions.add_parser("nsdl-backfill", help="the one-time private NSDL FPI back-fill (owner, 21 Oct 2026)")
    nsdl.add_argument("--through", type=_month, default=None, help="YYYY-MM (default: the last full month)")
    nsdl.set_defaults(func=cmd_nsdl_backfill)


def cmd_flows_table(args, out=print) -> int:
    from ..alerts.run_location import run_location
    from .wiring import archived_days, build_alerts, build_committers, build_flow_table_job, entered_sessions

    name = args.dataset
    result = build_flow_table_job(name).run(archived_days(name), entered_sessions(name))
    out(SUMMARY.format(name=name, entered=len(result.entered), rewritten=len(result.rewritten),
                       waiting=len(result.waiting)))  # fmt: skip
    problems = list(result.problems)
    for committer in build_committers():
        outcome = committer.commit(f"flows table {name}")
        out(outcome)
        if NOT_COMMITTED in outcome:
            problems.append(outcome)
    for line in problems:
        out(line)
    if not problems:
        return 0
    first = "; ".join(problems[:SHOWN_IN_ALERT])
    out(build_alerts().send(ALERT.format(name=name, count=len(problems), first=first, where=run_location())))
    return 1


def month_ends(first: date, through: date) -> list[date]:
    """The last calendar day of every month from `first`'s to `through`'s (NSDL accepts any day as "To Date")."""
    ends, year, month = [], first.year, first.month
    while (year, month) <= (through.year, through.month):
        ends.append(date(year, month, calendar.monthrange(year, month)[1]))
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return ends


def cmd_nsdl_backfill(args, out=print, today=None) -> int:
    from ..alerts.run_location import run_location
    from ..storage.data_wiring import build_receipt_committer
    from .wiring import build_alerts, build_nsdl_backfill

    current = today or today_local()
    through = args.through or date(current.year, current.month, 1) - timedelta(days=1)
    result = build_nsdl_backfill().run(month_ends(NSDL_FIRST_MONTH, through))
    out(NSDL_SUMMARY.format(saved=len(result.saved), rows=result.rows, empty=len(result.empty),
                            skipped=len(result.skipped), failed=len(result.failed)))  # fmt: skip
    for month, why in sorted(result.failed.items()):
        out(NSDL_FAILED.format(month=month, why=why))
    out(build_receipt_committer().commit("nsdl-backfill"))
    if not result.failed:
        return 0
    months = ", ".join(f"{m:%Y-%m}" for m in sorted(result.failed))
    out(build_alerts().send(NSDL_ALERT.format(count=len(result.failed), months=months, where=run_location())))
    return 1


def _month(text: str) -> date:
    first = datetime.strptime(text, "%Y-%m").date()
    return date(first.year, first.month, calendar.monthrange(first.year, first.month)[1])
