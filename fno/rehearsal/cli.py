"""`python -m fno rehearse check` (story REH1a, judge 557): the guard, run in a process started through the package's
real entry point with the mode set, so the replay clock and the HTTP guard it installs are what is checked. Prints
one line per problem and exits 1 on any; prints nothing and exits 0 when the rehearsal is safe. And `rehearse
preopen|morning|evening --day D` (story REH1c): the other three routines' rehearsals."""

from __future__ import annotations

NOT_REHEARSING = "rehearse check: FNO_REHEARSAL is not set: nothing to check"


def add_rehearse_parser(subparsers) -> None:
    from datetime import date

    from .routines import ROUTINES

    rehearse = subparsers.add_parser("rehearse", help="story REH1: a recorded day replayed safely")
    actions = rehearse.add_subparsers(dest="rehearse_cmd", required=True)
    actions.add_parser("check", help="the rehearsal guard, inside a rehearsing process").set_defaults(func=cmd_check)
    for name, routine in ROUTINES.items():
        if name != "daily":  # the daily run's is `daily run --rehearse`
            one = actions.add_parser(name, help=f"replay a recorded day's {routine.section!r} routine (REH1c)")
            one.add_argument("--day", type=date.fromisoformat, required=True, help="the recorded session day")
            one.set_defaults(func=cmd_routine, routine=name)


def cmd_routine(args, out=print) -> int:
    from ..config import ROOT
    from .rehearse import rehearse
    from .routines import ROUTINES

    return rehearse(ROUTINES[args.routine], args.day, ROOT, out)


def cmd_check(args, out=print) -> int:
    from .guard import problems
    from .mode import rehearsal
    from .process_checks import process_problems

    mode = rehearsal()
    if mode is None:
        out(NOT_REHEARSING)
        return 1
    found = process_problems(mode) + problems()
    for line in found:
        out(line)
    return 1 if found else 0
