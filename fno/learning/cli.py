"""Commands of story LR1 (the weekly post-mortem; it reports and decides no trade):

python -m fno postmortem weekly [--week-ending YYYY-MM-DD] [--post]  # print; --post: write research/postmortems/
python -m fno postmortem fire [--week-ending YYYY-MM-DD]             # fire the AI routine (after the lines are pushed)
python -m fno postmortem publish [--week-ending YYYY-MM-DD]          # check the AI's files, post once to #fno-desk
"""

from __future__ import annotations

from datetime import date


def add_postmortem_parser(subparsers) -> None:
    parser = subparsers.add_parser("postmortem", help="the weekly post-mortem: forecasts, weather, data health (LR1)")
    actions = parser.add_subparsers(dest="postmortem_cmd", required=True)
    for name, text in (("weekly", "build the week's lines"), ("fire", "fire the post-mortem routine"),
                       ("publish", "post the checked report once")):  # fmt: skip
        action = actions.add_parser(name, help=text)
        action.add_argument("--week-ending", type=date.fromisoformat, help="a Saturday (default: the latest, IST)")
    actions.choices["weekly"].add_argument("--post", action="store_true", help="write the lines to the repository")
    parser.set_defaults(func=cmd_postmortem)


def cmd_postmortem(args) -> int:
    from ..models import now_ist
    from . import wiring
    from .week import latest_saturday

    saturday = args.week_ending or latest_saturday(now_ist().date())
    if args.postmortem_cmd == "fire":
        print(wiring.build_routine().fire(saturday))
        return 0
    if args.postmortem_cmd == "publish":
        print("\n".join(wiring.build_publisher().publish(saturday)))
        return 0
    return _weekly(wiring, saturday, args.post)


def _weekly(wiring, saturday: date, post: bool) -> int:
    from .report import PostMortemConflict

    report = wiring.build_builder().build(wiring.week_of(saturday))
    print(report.text, end="")
    if not post:
        return 0
    try:
        print(f"post-mortem {saturday}: {wiring.build_records().write(saturday, report)}")
    except PostMortemConflict as conflict:
        print(conflict)
        return 1
    return 0
