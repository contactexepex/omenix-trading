"""`python -m fno role-value report` (story F9a): the role-value report of book 2 or 3 over a period, as Markdown.
Verdicts appear only with `--review` on a scheduled review date. It reads records only; it never fires a session,
changes a role or places an order."""

from __future__ import annotations

from datetime import date

from ..constants import AI_BOOKS

EXIT_REFUSED = 2


def add_role_value_parser(subparsers) -> None:
    parser = subparsers.add_parser("role-value", help="does each AI role earn its cost? (story F9a)")
    actions = parser.add_subparsers(dest="role_value_cmd", required=True)
    report = actions.add_parser("report", help="one book's role-value report over a period")
    report.add_argument("--book", choices=AI_BOOKS, required=True)
    report.add_argument("--from", dest="first", type=date.fromisoformat, required=True)
    report.add_argument("--to", dest="last", type=date.fromisoformat, required=True)
    report.add_argument("--common-start", type=date.fromisoformat, required=True, help="S1's common start")
    report.add_argument("--review", action="store_true", help="judge the units (only on a scheduled review date)")
    parser.set_defaults(func=cmd_role_value)


def cmd_role_value(args) -> int:
    from ..config import load_app_config
    from .checks import RowRefused
    from .render import render
    from .report import Period
    from .role_set import RoleSetError
    from .wiring import build_role_value_report

    period = Period(args.book, args.first, args.last, args.common_start, args.review)
    try:
        result = build_role_value_report(load_app_config()).build(period)
    except (RowRefused, RoleSetError, ValueError) as refused:
        print(f"refused: {refused}")
        return EXIT_REFUSED
    print(render(result), end="")
    return 0
