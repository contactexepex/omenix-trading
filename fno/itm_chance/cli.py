"""`python -m fno itmchance <calibrate|chances>` (story G13c). Read-only towards NSE and Groww; never trades.

- calibrate [--underlying U]: syncs G13's records and G13c's reports through the verified Drive cache, settles every
  expiry on file, and writes one calibration report per underlying to Drive (write-once, with its receipt; commit
  `receipts/` after). Nothing is written while no expiry is settled, or when a report for the same last settled
  expiry is already in Drive.
- chances --day D --underlying U: prints that day's chances from the cache (writes nothing).
"""

from __future__ import annotations

from datetime import date

import requests

from ..models import now_ist
from ..price_distribution.cli import CACHE_PREFIX as G13_PREFIX
from ..price_ranges.constants import UNDERLYINGS  # NIFTY and BANKNIFTY, as G13b
from ..storage.owner_token import DriveSignInRefused
from ..storage.raw_store import RawFileConflict
from .constants import MEASURE
from .folders import CALIBRATION, DATA_AREA

OWN_PREFIX = f"{DATA_AREA}/{CALIBRATION}"
STOPPING_FAILURES = (requests.RequestException, DriveSignInRefused, RawFileConflict, RuntimeError, OSError)
SYNC_PROBLEMS = "STOPPED: the Drive cache could not verify every file: {problems}"
CHANCE_LINE = "{expiry} {days:>3}d {strike:>9g} {side} {chance:.4f} {region} {source}"


def add_itmchance_parser(subparsers) -> None:
    p = subparsers.add_parser("itmchance", help="G13c: each contract's market-implied ITM chance and its calibration")
    p.add_argument("action", choices=("calibrate", "chances"))
    p.add_argument("--underlying", default=None, help="NIFTY or BANKNIFTY (calibrate: default both)")
    p.add_argument("--day", type=date.fromisoformat, default=None, help="chances: YYYY-MM-DD")
    p.set_defaults(func=cmd_itmchance)


def cmd_itmchance(args) -> int:
    try:
        return {"calibrate": _calibrate, "chances": _chances}[args.action](args)
    except STOPPING_FAILURES as exc:
        print(f"STOPPED ({type(exc).__name__}): {exc}")
        return 1


def _synced() -> bool:
    from ..storage.data_wiring import build_drive_cache

    cache = build_drive_cache()
    for prefix in (G13_PREFIX, OWN_PREFIX):
        report = cache.sync(prefix)
        if not report.complete:
            print(SYNC_PROBLEMS.format(problems="; ".join(report.problems)))
            return False
    return True


def _calibrate(args) -> int:
    from .publish import publish
    from .records import cached_records
    from .report import calibration_report, summary_lines
    from .wiring import build_settle, build_store, data_root, methods

    if not _synced():
        return 1
    found, root = methods(), data_root()
    records = list(cached_records(root, found["g13"]))
    settle, store = build_settle(), build_store()
    for underlying in (args.underlying,) if args.underlying else UNDERLYINGS:
        report = calibration_report(underlying, records, settle, now_ist().date(), found)
        print("\n".join([*summary_lines(report), publish(report, root, store)]))
    return 0


def _chances(args) -> int:
    from .reader import ItmChances
    from .wiring import data_root, methods

    if args.day is None or args.underlying is None or not _synced():
        print("chances needs --day and --underlying, and a verified cache")
        return 1
    chances = ItmChances(data_root(), methods()["g13"]).for_day(args.underlying, args.day)
    print(f"{args.underlying} {args.day}: {len(chances)} contracts; {MEASURE}")
    for c in chances:
        print(CHANCE_LINE.format(expiry=c.expiry, days=c.days, strike=c.strike, side=c.side, chance=c.itm_chance,
                                 region=c.region, source=c.source))  # fmt: skip
    return 0
