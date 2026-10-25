"""`python -m fno pricerange <issue|backfill|closes|score>` (story G13b, part A).

- issue --at 1545 [--day D] --live: the live 15:45 issue, run by O1's `price_ranges` step (see `issuer.py`).
- backfill --from D1 --to D2 --source {eod,3pm}: rebuilds a range; commit `receipts/` after.
- closes --to D: extends BANKNIFTY's close table from the archived index-close files (2017 on the first time).
- score: scores every resolved row (live ones only when sealed), writes the report FL1 reads and prints its summary.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import date, timedelta

import requests

from ..config import ROOT, load_app_config
from ..models import now_ist
from ..research_data.calendar import CalendarError
from ..storage.owner_token import DriveSignInRefused
from ..storage.raw_store import RawFileConflict
from .build import CAPTURE, CLOSE
from .closes import Outcomes
from .constants import BACKFILL_3PM, BACKFILL_EOD, ISSUE_1545, UNDERLYINGS
from .folders import ROOT as ROOT_FOLDER
from .folders import drive

STOPPING = (requests.RequestException, DriveSignInRefused, RawFileConflict, RuntimeError, CalendarError, OSError)
V6A_FILE = ROOT / "research" / "forecasts" / "v4" / "v6_ewma_t4" / "v6_abs_move_2pct_next_session.csv"
CACHE_PREFIX = drive(ROOT_FOLDER)  # a folder path: the receipt folder refuses a trailing "/"
SUMMARY = "{label} {underlying} {issue} {horizon} {forecaster}: n={n} QS={qs:.5f} 50%={c50} 90%={c90} Brier={brier:.3f}"


def add_pricerange_parser(subparsers) -> None:
    p = subparsers.add_parser("pricerange", help="G13b: NIFTY and BANKNIFTY price ranges at N1 and N3 (15:45)")
    p.add_argument("action", choices=("issue", "backfill", "closes", "score"))
    p.add_argument("--at", default=ISSUE_1545, choices=(ISSUE_1545,), help="issue time (1545 only in phase 1)")
    p.add_argument("--day", type=date.fromisoformat, default=None)
    p.add_argument("--from", dest="start", type=date.fromisoformat, default=None)
    p.add_argument("--to", dest="end", type=date.fromisoformat, default=None)
    p.add_argument("--source", default=None, help="backfill: eod or 3pm")
    p.add_argument("--live", action="store_true", help="issue: O1's daily step only (a hand run writes no live row)")
    p.set_defaults(func=cmd_pricerange)


def cmd_pricerange(args) -> int:
    action = {"issue": _issue, "backfill": _backfill, "closes": _closes, "score": _score}[args.action]
    try:
        return action(args, load_app_config())
    except STOPPING as exc:
        print(f"STOPPED ({type(exc).__name__}): {exc}")
        return 1


def _issue(args, cfg) -> int:
    from .wiring import build_issuer

    code, lines = build_issuer(cfg).issue(args.day or now_ist().date(), live=args.live)
    print("\n".join(lines))
    return code


def _backfill(args, cfg) -> int:
    from .wiring import build_backfill

    if args.start is None or args.end is None or args.source not in ("eod", "3pm"):
        print("backfill needs --from, --to and --source eod|3pm")
        return 2
    eod = args.source == "eod"
    label, basis = (BACKFILL_EOD, CLOSE) if eod else (BACKFILL_3PM, CAPTURE)
    run = build_backfill(cfg, eod, range(args.start.year, args.end.year + 1) if eod else None)
    print("\n".join(run.run(label, basis, UNDERLYINGS, args.start, args.end)))
    print("commit receipts/data/price_ranges/ (files count once their receipts are committed)")
    return 0


def _closes(args, cfg) -> int:
    from .wiring import BANKNIFTY, build_table_update

    tables, files = build_table_update()
    print("\n".join(tables.update(BANKNIFTY, files, args.end or now_ist().date())))
    return 0


def v6a(day: str) -> float | None:
    """v4's V6a forecast of the day by its rule forecaster, if recorded (G7's layout; read for a report line only)."""
    if not V6A_FILE.is_file():
        return None
    with open(V6A_FILE, newline="", encoding="utf-8") as file:
        row = next((r for r in csv.DictReader(file) if r["day"] == day and r["status"] == "ok"), None)
    return float(row["value"]) if row else None


def _score(args, cfg) -> int:
    from .folders import scores_path
    from .reader import RangeForecasts
    from .scores import score_report
    from .wiring import CACHE_ROOT, build_closes, build_seals, build_store, build_tables, seal_lines

    store = build_store()
    tables = build_tables(store)
    report = tables.cache.sync(CACHE_PREFIX)
    if not report.complete:
        print(f"STOPPED: the Drive cache could not verify every file: {'; '.join(report.problems)}")
        return 1
    seals = build_seals(store)
    sealed = seal_lines(seals, store, now_ist().date() + timedelta(days=1))  # today's issue included
    reader, outcomes = RangeForecasts(CACHE_ROOT, seals), Outcomes(build_closes(tables))
    records = [(s.record, not s.late) for s in reader.live()] + [(r, True) for r in reader.backfill()]
    result = score_report(records, lambda u, d: outcomes.close(u, date.fromisoformat(d)), v6a)
    data = (json.dumps(result, sort_keys=True, indent=1) + "\n").encode()
    path = scores_path(now_ist(), hashlib.sha256(data).hexdigest())
    store.put(path, data)
    for g in result["groups"]:
        c50 = "n/a" if g["inside_50"] is None else f"{g['inside_50']:.0%}"
        c90 = "n/a" if g["inside_90"] is None else f"{g['inside_90']:.0%}"
        print(SUMMARY.format(qs=g["mean_qs"], c50=c50, c90=c90, brier=g["brier_up"], **g))
    print("\n".join([*sealed, *result["notes"], f"late live rows: {result['late_rows']}", f"report written: {path}"]))
    return 0
