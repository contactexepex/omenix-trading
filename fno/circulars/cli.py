"""`python -m fno circulars [--day D]`: NSE's and SEBI's circular lists, first-seen times and F&O files (story A20b)."""

from __future__ import annotations

from datetime import date


def add_circulars_parser(subparsers) -> None:
    p = subparsers.add_parser("circulars", help="list new NSE and SEBI circulars, keep F&O files in Drive (A20b)")
    p.add_argument("--day", type=date.fromisoformat, help="YYYY-MM-DD the run is for (default: today, IST)")
    p.set_defaults(func=cmd_circulars)


def cmd_circulars(args) -> int:
    from ..models import now_ist
    from .wiring import build_circulars_job

    return build_circulars_job().run(args.day or now_ist().date())
