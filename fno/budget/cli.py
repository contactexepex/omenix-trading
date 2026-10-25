"""`python -m fno budget <action>` (stories F8 and BG1). Research and bookkeeping only; posts nothing.

- `meter`: the month's costs by item (design v2 section 8.1), the allocated plan cost apart from cash spend, the AI cap;
- `signal`: writes the month's signal file (`accounting/budget/<YYYY-MM>_signal.json`) and dry-runs its alert;
- `stop-rule`: the stop-rule review date, days left, and which inputs of Test A and Test B exist yet;
- `record-usage`: adds one session's complete days to `accounting/ai_usage.csv` from a session export, or from a
  routine's own timing of its run (`--self-timed`, owner's "5 A") (F8);
- `record-roster`: merges a `list_sessions` export into `accounting/ai_session_roster.csv`, so the meter knows which
  development sessions exist.
Exports hold reply texts, so they must live outside the repository; a path inside it is refused.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from ..constants import AI_BOOKS
from .constants import PURPOSE_DATA_ROUTINES, USAGE_PURPOSES


def add_budget_parser(subparsers) -> None:
    budget = subparsers.add_parser("budget", help="AI usage, the budget meter and the stop-rule tracker (F8, BG1)")
    actions = budget.add_subparsers(dest="budget_cmd", required=True)
    for name, text in (("meter", "print the month's budget meter"),
                       ("signal", "write the month's budget signal and dry-run its alert")):  # fmt: skip
        actions.add_parser(name, help=text).add_argument("--month", help="YYYY-MM (default: this month in IST)")
    actions.add_parser("stop-rule", help="the stop-rule review date and its inputs")
    record = actions.add_parser("record-usage", help="record one session's usage from its export (written once)")
    record.add_argument("--export", type=Path, required=True, help="the JSON a Claude session saved (outside git)")
    record.add_argument("--self-timed", action="store_true", help="the file is a routine's own timing of its run")
    record.add_argument("--purpose", required=True, choices=USAGE_PURPOSES)
    record.add_argument("--book", default="", choices=("", *AI_BOOKS))
    record.add_argument("--role", default="", help="the role or bundle the session worked for")
    roster = actions.add_parser("record-roster", help="merge a list_sessions export into the session roster")
    roster.add_argument("--export", type=Path, required=True, help="the JSON a Claude session saved (outside git)")
    budget.set_defaults(func=cmd_budget)


def cmd_budget(args) -> int:
    from ..models import now_ist
    from .usage_reader import ExportRefused

    today = now_ist().date()
    commands = {"meter": _meter, "signal": _signal, "stop-rule": _stop_rule, "record-usage": _record_usage,
                "record-roster": _record_roster}  # fmt: skip
    try:
        return commands[args.budget_cmd](args, today)
    except (ExportRefused, ValueError, OSError) as refused:  # every refusal says why; none is a traceback
        print(f"refused: {refused}")
        return 1


def _month(args, today: date) -> str:
    month = getattr(args, "month", None) or f"{today:%Y-%m}"
    try:
        date.fromisoformat(month + "-01")
    except ValueError:
        raise ValueError(f"--month {month!r} is not YYYY-MM") from None
    return month


def _outside_repository(path: Path) -> Path:
    from ..config import ROOT

    if path.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError(f"{path} is inside the repository: exports hold reply texts, keep them outside it")
    return path


def _meter(args, today: date) -> int:
    from .report import meter_lines
    from .wiring import build_month_meter

    print("\n".join(meter_lines(build_month_meter(_month(args, today), today))))
    return 0


def _signal(args, today: date) -> int:
    from ..config import ROOT
    from ..models import now_ist
    from .signal import send_alert, signal_data, write_signal
    from .wiring import build_budget_alert_sender, build_month_meter

    meter = build_month_meter(_month(args, today), today)
    data = signal_data(meter.month, meter.cap, len(meter.missing_captures), now_ist())
    print(f"signal {data['level']} written: {write_signal(ROOT, data).relative_to(ROOT)}")
    print(send_alert(build_budget_alert_sender(), data))
    return 0


def _stop_rule(args, today: date) -> int:
    from ..config import ROOT
    from .report import stop_rule_lines
    from .stop_rule_tracker import review_reached
    from .wiring import build_budget_alert_sender, build_review_date

    review = build_review_date()
    print("\n".join(stop_rule_lines(ROOT, review, today)))
    if alert := review_reached(review, today):
        print(build_budget_alert_sender().send(alert))
    return 0


def _record_usage(args, today: date) -> int:
    from .usage_ledger import Attribution
    from .wiring import build_data_routine_names, build_usage_ledger, build_usage_reader

    reader = build_usage_reader(_outside_repository(args.export), args.self_timed)
    if args.purpose == PURPOSE_DATA_ROUTINES and args.role not in (names := build_data_routine_names()):
        raise ValueError(f"--role {args.role!r} is not a data routine of budget.data_routines {names}")
    who = Attribution(args.purpose, args.book, args.role)
    print("\n".join(build_usage_ledger().record(reader.days(), who, reader.complete_before(today))))
    return 0


def _record_roster(args, today: date) -> int:
    from .session_roster import read_roster_export
    from .wiring import build_session_roster

    sessions = read_roster_export(_outside_repository(args.export))
    print(f"roster: {build_session_roster().record(sessions)} session(s) listed")
    return 0
