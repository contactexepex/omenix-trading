"""`python -m fno preopen record [--day D]` (story A22): the morning capture, run by the 08:36 IST Claude routine."""

from __future__ import annotations

from datetime import date


def add_preopen_parser(subparsers) -> None:
    p = subparsers.add_parser("preopen", help="GIFT Nifty and NSE's pre-open result, by 09:12 IST (A22)")
    actions = p.add_subparsers(dest="preopen_action", required=True)
    record = actions.add_parser("record", help="capture today's GIFT Nifty and pre-open values")
    record.add_argument("--day", type=date.fromisoformat, help="YYYY-MM-DD (default: today, IST)")
    record.set_defaults(func=cmd_preopen_record)


def cmd_preopen_record(args) -> int:
    from ..config import load_app_config
    from ..models import now_ist
    from .wiring import build_preopen_recorder

    return build_preopen_recorder(load_app_config(args.config)).record(args.day or now_ist().date())
