"""`python -m fno scoreboard b|a [--on YYYY-MM-DD]`: scoreboard B, whole systems (story S2), and scoreboard A, matched
decisions (story S3), from the paper records, written to `research/scoreboards/<B|A>/<date>.json` and kept in Drive,
never committed (story E2c: they hold marked results and one-lot fills). Research only: they read records and place
nothing."""

from __future__ import annotations

from datetime import date

LINE = "{book}: {state}"


def add_scoreboard_parser(subparsers) -> None:
    board = subparsers.add_parser("scoreboard", help="the books' scoreboards (epic S)")
    which = board.add_subparsers(dest="scoreboard_cmd", required=True)
    whole = which.add_parser("b", help="scoreboard B, whole systems: each book's paper account (story S2)")
    whole.add_argument("--on", type=date.fromisoformat, help="the last day counted (default today, IST)")
    matched = which.add_parser("a", help="scoreboard A, matched decisions: one-lot units on the common set (story S3)")
    matched.add_argument("--on", type=date.fromisoformat, help="the last day counted (default today, IST)")
    board.set_defaults(func=cmd_scoreboard)


def header(name: str, board: dict) -> str:
    start = board["common_start"] or "not reached"
    return f"scoreboard {name} {board['date']} ({board['protocol']}); common start {start}"


def summary(board: dict) -> list[str]:
    lines = [header("B", board)]
    for book, entry in board["books"].items():
        if "overall" not in entry:
            lines.append(LINE.format(book=book, state=entry["account"]))
            continue
        overall, ok = entry["overall"], entry["reconciliation"]["ok"]
        money = f"raw account net Rs {overall['raw_account_net_rs']:,.2f}, {overall['trades']['positions']} positions"
        state = f"{money}, {'reconciles' if ok else 'DOES NOT RECONCILE'} with C1"
        lines.append(LINE.format(book=book, state=state))
    return lines


def matched_summary(board: dict) -> list[str]:
    lines = [header("A", board)]
    for book, entry in board["books"].items():
        misses = f"{entry['misses']} of {entry['eligible_days']} eligible days missed"
        lines.append(LINE.format(book=book, state=f"{entry['verdict']}; {misses}"))
    return lines


def cmd_scoreboard(args) -> int:
    from ..config import ROOT, load_app_config
    from ..desk.wiring import download_private_records
    from ..models import now_ist
    from . import matched_board, whole_system
    from .wiring import build_matched_board, build_whole_system_board

    files, cfg, on = download_private_records(), load_app_config(), args.on or now_ist().date()
    if args.scoreboard_cmd == "a":
        board = build_matched_board(cfg).build(on)
        path = matched_board.write_board(ROOT, board)
        lines = matched_summary(board)
    else:
        board = build_whole_system_board(cfg).build(on)
        path, lines = whole_system.write_board(ROOT, board), summary(board)
    files.push([path])
    print("\n".join([*lines, f"written {path.relative_to(ROOT)} and kept in Drive (never committed)"]))
    return 0
