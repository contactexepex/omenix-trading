"""`capture-gate`: the read-only capture-gate run (story MS-P1b). Prints one counts-only line per road for the last 10
trading sessions up to a day; reads stored files only and writes nothing. `python -m fno.school.quality.command`
until the join-up story (MS-P1j) registers it as `python -m fno school capture-gate`."""

import argparse
from collections.abc import Callable
from datetime import date, datetime, time, timedelta

from ...models import now_ist
from .capture_gate import CaptureGateReport
from .options import add_through
from .wiring import build_capture_gate_report

LAST_CAPTURE_TIME = time(15, 15)


def run(through: date, report: CaptureGateReport | None = None, out: Callable[[str], None] = print) -> int:
    """Prints a road's line each; the exit code is always 0, because a closed road is a result, not a failure."""
    for line in (report or build_capture_gate_report()).lines(through):
        out(line)
    return 0


def default_through(now: datetime) -> date:
    """Today once its captures can exist (after the last window, 15:13), else yesterday: an early run must not report
    today's captures as missing."""
    return now.date() if now.time() >= LAST_CAPTURE_TIME else now.date() - timedelta(days=1)


def run_args(args: argparse.Namespace) -> int:
    """The parsed `--through` (or its default day), however the command was reached."""
    return run(args.through or default_through(now_ist()))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="capture-gate", description=__doc__)
    add_through(parser)
    return run_args(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
