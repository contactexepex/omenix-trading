"""`python -m fno desk pack [--day YYYY-MM-DD]` (story E2): builds and writes the day's common market pack and Book 1's
private pack, printing each path and SHA-256 (commit them with the day's run). Books 2 and 3 get private packs when
their envelope (D4) and constitution (D5) exist. Research and paper only: nothing here places an order."""

from __future__ import annotations

from datetime import date

EXIT_REFUSED = 2


def add_pack_command(actions) -> None:
    """`desk pack`, registered by the desk's one parser (`fno/desk/cli.py`)."""
    pack = actions.add_parser("pack", help="write the common market pack and Book 1's private pack for a day")
    pack.add_argument("--day", type=date.fromisoformat, help="the session day (default: today in IST)")
    pack.set_defaults(func=cmd_pack)


def cmd_pack(args) -> int:
    from ..config import ROOT
    from ..models import now_ist
    from .pack_items import PackError
    from .pack_wiring import build_packs
    from .wiring import build_private_files

    files = build_private_files()
    day, packs = args.day or now_ist().date(), build_packs(files=files)
    try:
        files.download()  # story E2c: the private packs hold each account's text, read from Drive first
        common = packs.build(day)
    except PackError as refused:
        print(f"refused: {refused}")
        return EXIT_REFUSED
    for path, sha256 in packs.written(day):
        print(f"wrote {path.relative_to(ROOT)} sha256 {sha256}")
    print(f"refused items (after the cutoff or untimed): {len(common.body['refused'])}")
    return 0
