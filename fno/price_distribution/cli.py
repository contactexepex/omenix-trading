"""`python -m fno pricedist <record|value|backfill|score>` (story G13).

- record [--day D]: the live day record, run by O1's `price_distribution` step (see `recorder.py` for its lines).
- value --day D --source {groww,nse} --dry-run: prints one day's record and writes nothing (no Drive, no receipt).
- backfill --from D1 --to D2 --source {3pm,eod}: rebuilds a range from captured inputs; commit `receipts/` after.
- score: scores every resolved row read through the verified Drive cache; writes the report and prints it.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date

import requests

from ..config import load_app_config
from ..constants import NIFTY_SYMBOL
from ..models import now_ist
from ..research_data.calendar import CalendarError
from ..storage.owner_token import DriveSignInRefused
from ..storage.raw_store import RawFileConflict
from .constants import BACKFILL_3PM, BACKFILL_EOD, SOURCE_GROWW, SOURCE_NSE
from .folders import DATA_AREA, ROOT
from .records import encode

STOPPING_FAILURES = (requests.RequestException, DriveSignInRefused, RawFileConflict, RuntimeError, CalendarError,
                     OSError)  # fmt: skip
NO_CHAIN_LINE = "nothing written: no {source} chain for {underlying} on {day}"
SYNC_PROBLEMS = "STOPPED: the Drive cache could not verify every file: {problems}"
REPORT_WRITTEN = "report written: {path}"
CACHE_PREFIX = f"{DATA_AREA}/{ROOT}"  # a folder path: the receipt folder refuses a trailing "/"


def add_pricedist_parser(subparsers) -> None:
    p = subparsers.add_parser("pricedist", help="G13: valuation record and NIFTY price-distribution forecasts")
    p.add_argument("action", choices=("record", "value", "backfill", "score"))
    p.add_argument("--day", type=date.fromisoformat, default=None, help="YYYY-MM-DD (record: default today IST)")
    p.add_argument("--source", default=None, help="value: groww or nse; backfill: 3pm or eod")
    p.add_argument("--from", dest="start", type=date.fromisoformat, default=None)
    p.add_argument("--to", dest="end", type=date.fromisoformat, default=None)
    p.add_argument("--underlying", default=None, help="value/backfill: one underlying (default NIFTY / all)")
    p.add_argument("--dry-run", action="store_true", help="value: always a dry run (writes nothing)")
    p.add_argument("--live", action="store_true", help="record: O1's daily step only (a hand run writes no live row)")
    p.set_defaults(func=cmd_pricedist)


def cmd_pricedist(args) -> int:
    action = {"record": _record, "value": _value, "backfill": _backfill, "score": _score}[args.action]
    try:
        return action(args, load_app_config())
    except STOPPING_FAILURES as exc:
        print(f"STOPPED ({type(exc).__name__}): {exc}")
        return 1


def _record(args, cfg) -> int:
    from .wiring import build_live_recorder

    code, lines = build_live_recorder(cfg).record(args.day or now_ist().date(), live=args.live)
    print("\n".join(lines))
    return code


def _value(args, cfg) -> int:
    from .wiring import build_chains, build_day_builder

    if args.day is None or args.source not in (SOURCE_GROWW, SOURCE_NSE):
        print("value needs --day and --source groww|nse")
        return 2
    underlying = args.underlying or NIFTY_SYMBOL
    chain = build_chains((args.source,)).chain(underlying, args.day)
    if chain is None:
        print(NO_CHAIN_LINE.format(source=args.source, underlying=underlying, day=args.day))
        return 1
    print(encode(build_day_builder(cfg).build(chain, BACKFILL_3PM, None)).decode(), end="")
    return 0


def _backfill(args, cfg) -> int:
    from .wiring import UNDERLYINGS, build_backfill

    if args.start is None or args.end is None or args.source not in ("3pm", "eod"):
        print("backfill needs --from, --to and --source 3pm|eod")
        return 2
    eod = args.source == "eod"
    years = range(args.start.year, args.end.year + 1) if eod else None
    underlyings = (NIFTY_SYMBOL,) if eod else ((args.underlying,) if args.underlying else UNDERLYINGS)
    label = BACKFILL_EOD if eod else BACKFILL_3PM
    print("\n".join(build_backfill(cfg, eod, years).run(label, underlyings, args.start, args.end)))
    print("commit receipts/data/price_distribution/ (files count once their receipts are committed)")
    return 0


def _score(args, cfg) -> int:
    from .folders import scores_path
    from .record_files import read_records
    from .score_report import score_report, summary_lines
    from .wiring import build_closes, build_score_inputs

    cache, root, store = build_score_inputs()
    report = cache.sync(CACHE_PREFIX)
    if not report.complete:
        print(SYNC_PROBLEMS.format(problems="; ".join(report.problems)))
        return 1
    result = score_report(read_records(root / DATA_AREA), build_closes())
    data = (json.dumps(result, sort_keys=True, indent=1) + "\n").encode()
    path = scores_path(now_ist().date(), hashlib.sha256(data).hexdigest())
    store.put(path, data)
    print("\n".join([*summary_lines(result), REPORT_WRITTEN.format(path=path)]))
    return 0
