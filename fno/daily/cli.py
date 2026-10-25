"""`python -m fno daily run [--day YYYY-MM-DD]` (story O1): the whole desk day in one command, ending on one line
("day done", "day done with problems: <steps>", or E3's stop line with "no card today"). Paper only: never places,
modifies or cancels an order."""

from __future__ import annotations

from datetime import date


def add_daily_parser(subparsers) -> None:
    daily = subparsers.add_parser("daily", help="the desk's day: weather, v4 forecasts, quotes, desk, card (O1)")
    actions = daily.add_subparsers(dest="daily_cmd", required=True)
    run = actions.add_parser("run", help="run the day's steps in order, each recorded in journal/runs/<date>.json")
    run.add_argument("--day", type=date.fromisoformat, help="the session day (default: today in IST)")
    run.add_argument(
        "--rehearse",
        action="store_true",
        help="replay the recorded day safely: Drive dryrun/, a rehearsal/ branch, labelled posts (REH1)",
    )
    run.set_defaults(func=cmd_daily_run)


def cmd_daily_run(args, out=print, root=None) -> int:
    """A second run of a day beside a living one does nothing and says so (story O1-day-lock)."""
    from ..config import ROOT, load_app_config
    from ..models import now_ist
    from .day_lock import ALREADY_RUNNING, DayLock
    from .part_locks import PART_LOCKS
    from .wiring import build_day_runner

    root, day = root or ROOT, args.day or now_ist().date()
    if getattr(args, "rehearse", False):
        from ..rehearsal.rehearse import rehearse_daily

        return rehearse_daily(day, root, out)
    with DayLock(root / PART_LOCKS).taken(day, now_ist()) as running_since:
        if running_since is not None:
            out(ALREADY_RUNNING.format(day=day, since=running_since))
            return 1
        code, line = build_day_runner(load_app_config(), root, day=day).run(day)
    out(line)
    return code
