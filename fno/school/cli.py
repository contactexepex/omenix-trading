"""`python -m fno school ...` (story MS-P1j): the session's run, its replay, and b's capture-gate report.

- `run [--session D]`: the paper record of the 15:00 slot, only when `school.enabled` is true; otherwise the record
  root returns the switched-off runner, which prints the school-off line and touches nothing (no store is built).
- `run --replay FOLDER [--session D]`: a recorded session again, every write under FOLDER (no Drive write, no push,
  no commit, a fixed clock). A replay writes no paper record, so its root has no switch; it is how the end-to-end
  dry run is made.
- `capture-gate [--through D]`: b's read-only report; the option is the gate's own (`quality/options.py`)."""

from collections import Counter
from datetime import date
from pathlib import Path

from ..config import load_app_config
from ..models import now_ist
from .constants import FLEET_STOPPED
from .quality.options import add_through

NOT_A_SESSION = "not a trading day: nothing scheduled"


def add_school_parser(sub) -> None:
    school = sub.add_parser("school", help="the market school pilot (paper only; story MS-P1)")
    commands = school.add_subparsers(dest="school_cmd", required=True)
    run = commands.add_parser("run", help="the 15:00 slot of one session: decide, seal, fill (paper only)")
    run.add_argument("--session", type=date.fromisoformat, default=None, help="YYYY-MM-DD (default: today, IST)")
    run.add_argument("--replay", type=Path, default=None, help="replay into this folder: no record, no push")
    run.set_defaults(func=cmd_run)
    gate = commands.add_parser("capture-gate", help="b's read-only capture-gate report")
    add_through(gate)
    gate.set_defaults(func=cmd_capture_gate)
    from .simulator.command import add_practice_parser  # the simulator's one command (story MS-SIM-d4)

    add_practice_parser(commands)


def cmd_run(args, out=print) -> int:
    cfg = load_app_config(args.config) if getattr(args, "config", None) else load_app_config()
    session = args.session or now_ist().date()
    from . import wiring
    from .contracts.fleet import RunMode
    from .fleet.quote_share import share_lines

    if args.replay is None:
        mode, fleet = RunMode.RECORD, wiring.build_fleet(cfg)
    else:
        from .replay_wiring import build_replay_fleet

        mode, fleet = RunMode.REPLAY, build_replay_fleet(cfg, session, args.replay)
    run = fleet.run(session, mode)
    for line in run_lines(run, share_lines):
        out(line)
    for line in run.warnings:
        out(line)
    # A stop or a warning fails the daily run's step, which alerts #fno-desk
    return 1 if run.status.startswith(FLEET_STOPPED) or run.warnings else 0


def run_lines(run, share_lines) -> list[str]:
    if run.status:
        return [run.status]
    if not run.decisions:
        return [NOT_A_SESSION]
    tally = Counter((r.decision.outcome.value, r.decision.reason) for r in run.decisions)
    lines = [f"school {run.session} ({run.mode}): {len(run.decisions)} decisions sealed, {len(run.fills)} fills"]
    lines += [f"  {outcome}{': ' + reason if reason else ''} x{n}" for (outcome, reason), n in sorted(tally.items())]
    return lines + [f"  {line}" for line in share_lines(run.decisions)]


def cmd_capture_gate(args) -> int:
    from .quality.command import run_args

    return run_args(args)
