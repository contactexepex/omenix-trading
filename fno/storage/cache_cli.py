"""`python -m fno data-cache sync <prefix>` (story O9b): brings every receipted Drive file under a prefix (e.g.
`data/vix`) into the local verified cache, so readers and the `data`-marked tests that run without network find them.
Exit 1 when a file is missing from Drive or holds other bytes (each named)."""

from __future__ import annotations

SYNCED = "{prefix}: {present} file(s) already in the cache, {downloaded} downloaded and verified"


def add_cache_parser(subparsers) -> None:
    cache = subparsers.add_parser("data-cache", help="bring receipted Drive files into the verified cache (O9b)")
    actions = cache.add_subparsers(dest="cache_action", required=True)
    sync = actions.add_parser("sync", help="sync every receipted file under a Drive prefix")
    sync.add_argument("prefix", help="a Drive path prefix inside the project folder, e.g. data/vix")
    sync.set_defaults(func=cmd_cache_sync)


def cmd_cache_sync(args, out=print) -> int:
    from .data_wiring import build_drive_cache

    report = build_drive_cache().sync(args.prefix)
    out(SYNCED.format(prefix=args.prefix, present=report.present, downloaded=len(report.downloaded)))
    for problem in report.problems:
        out(problem)
    return 0 if report.complete else 1
