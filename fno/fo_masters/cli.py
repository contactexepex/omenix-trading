"""`python -m fno fo-masters [--day D]`: NSE's daily F&O master files to Drive, point in time (story A20a)."""

from __future__ import annotations

from datetime import date


def add_fo_masters_parser(subparsers) -> None:
    p = subparsers.add_parser("fo-masters", help="archive NSE's F&O ban list and market lots (A20a)")
    p.add_argument("--day", type=date.fromisoformat, help="YYYY-MM-DD (default: today, IST)")
    p.set_defaults(func=cmd_fo_masters)


def cmd_fo_masters(args) -> int:
    from ..models import now_ist
    from .wiring import build_fo_masters_job

    return build_fo_masters_job().run(args.day or now_ist().date())
