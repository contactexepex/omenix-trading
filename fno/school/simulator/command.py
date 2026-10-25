"""`python -m fno school practice run` (story MS-SIM-d4): the simulator's one command. Practice only: it reads the
archive and the recorded captures, writes under its own folder, and prints a report whose every line says
`practice (simulator)`. It touches no pilot record and needs no pilot switch.

- `run --from D --to D [--roads CODE ...] [--home FOLDER] [--archive]`: the window is checked against DATA_SPEND first
  and refused by name if it asks for a road or a day that is not spent or exposed data (exit 2, nothing read or
  written). `--archive` (story MS-SIM-e) also saves the run to Drive with a receipt per file and reads each back; the
  report says `archived` only when every file is receipted and verified (exit 1 otherwise). Without it nothing leaves
  the home folder."""

from datetime import date
from pathlib import Path

from ...config import ROOT, load_app_config
from ...models import now_ist
from ..constants import RoadCode
from ..contracts.roads import ROADS
from ..settings import school_settings
from .archive.inputs import CodeNotCommitted, code_identity
from .archive.session import archive_practice
from .archive.wiring import build_practice_archive
from .practice.render import left_out_lines, line, render
from .practice.runner import PracticeRunner
from .practice.window import RunWindow, WindowRefused
from .practice.wiring import build_practice_parts
from .windows import PracticeWindows

DEFAULT_HOME = ROOT / "work" / "school_practice"
DEFAULT_ROADS = (RoadCode.NIFTY_MONTHLY, RoadCode.NIFTY_WEEKLY, RoadCode.BANKNIFTY_MONTHLY)
REFUSED_EXIT = 2


def add_practice_parser(commands) -> None:
    practice = commands.add_parser("practice", help="practise the pilot's rule drivers on archived history (simulator)")
    sub = practice.add_subparsers(dest="practice_cmd", required=True)
    run = sub.add_parser("run", help="run a window of past sessions, three spread scenarios; practice only")
    run.add_argument("--from", dest="first", type=date.fromisoformat, required=True, help="first day, YYYY-MM-DD")
    run.add_argument("--to", dest="last", type=date.fromisoformat, required=True, help="last day, YYYY-MM-DD")
    run.add_argument(
        "--roads", nargs="+", default=[r.value for r in DEFAULT_ROADS], choices=[r.code.value for r in ROADS]
    )
    run.add_argument(
        "--home", type=Path, default=DEFAULT_HOME, help="where the practice records go (never the pilot's)"
    )
    run.add_argument("--archive", action="store_true", help="save the run to Drive with receipts (default: local only)")
    run.set_defaults(func=cmd_practice_run)


def cmd_practice_run(args, out=print) -> int:
    cfg = load_app_config(args.config) if getattr(args, "config", None) else load_app_config()
    try:
        window = RunWindow(args.first, args.last, tuple(RoadCode(code) for code in args.roads))
        window.check(PracticeWindows(school_settings(cfg).first_counted))  # before anything is read or built
        code = code_identity(ROOT) if args.archive else None  # a run id names the code: before the long run, not after
        parts, skipped = build_practice_parts(cfg, now_ist().date(), ROOT / "research" / "data" / "quotes")
        runner = PracticeRunner(parts, Path(args.home) / f"{args.first}_{args.last}")
        report = runner.run(window)
    except (WindowRefused, CodeNotCommitted) as refused:
        out(line(f"refused: {refused}"))
        return REFUSED_EXIT
    outcome = archive_practice(report, window, runner, code, build_practice_archive, skipped) if args.archive else None
    for text in render(report, outcome.status_lines() if outcome else None):
        out(text)
    for text in left_out_lines(skipped):
        out(text)
    return 1 if outcome and not outcome.archived else 0
