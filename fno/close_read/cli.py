"""`python -m fno closes read [--recheck]` (story A4h), run by O1's `close_read` (15:40) and `close_recheck` (16:00)
steps, the run's last two after `candles`; a hand run the same evening counts too (the NSE stamp decides, not the
clock). A run outside O1 (by hand, or the owner's evening task) adds `--commit`: it then commits and pushes A4h's own
receipts itself, and exits 1 when they are NOT committed."""

from __future__ import annotations

from .constants import READ, RECHECK

NOT_COMMITTED_MARK = "NOT committed"  # fno/storage/manifest_commit.py's NOT_COMMITTED


def add_closes_parser(subparsers) -> None:
    p = subparsers.add_parser("closes", help="A4h: today's index closes read from NSE after 15:30 (provisional)")
    p.add_argument("action", choices=("read",))
    p.add_argument("--recheck", action="store_true", help="the 16:00 second read, compared with the first")
    p.add_argument("--commit", action="store_true", help="outside O1: commit and push A4h's own receipts")
    p.set_defaults(func=cmd_closes)


def cmd_closes(args, out=print) -> int:
    from .wiring import build_close_reader, build_receipts_committer

    code = build_close_reader().run(RECHECK if args.recheck else READ)
    if not args.commit:
        return code
    line = build_receipts_committer().commit("A4h close read")
    out(line)
    return 1 if NOT_COMMITTED_MARK in line else code
