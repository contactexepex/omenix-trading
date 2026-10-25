"""`python -m fno capture-probe` (story MS-P0b): today's probe session, run by hand, read-only; `--dry-run
FOLDER [--session D]` runs the same code over made-up answers with everything written under FOLDER."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from ..config import load_app_config
from ..models import now_ist


def add_probe_parser(sub) -> None:
    probe = sub.add_parser("capture-probe", help="P0b: futures and stock chains at a study pace (read only)")
    probe.add_argument("--dry-run", type=Path, default=None, help="made-up answers; write under this folder only")
    probe.add_argument("--session", type=date.fromisoformat, default=None, help="dry run only: YYYY-MM-DD")
    probe.set_defaults(func=cmd_capture_probe)


def cmd_capture_probe(args, out=print) -> int:
    from . import wiring

    if args.dry_run is None:
        if args.session is not None:
            out("p0b: --session is for a dry run only; the live probe reads today")
            return 2
        cfg = load_app_config(args.config) if getattr(args, "config", None) else load_app_config()
        return wiring.build_probe_day(cfg).run(now_ist().date(), out)
    session = args.session or now_ist().date()
    return wiring.build_dry_run_day(session, args.dry_run).run(session, out)
