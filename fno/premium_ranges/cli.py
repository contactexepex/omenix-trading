"""`python -m fno premrange <issue|score>` (story G13d). Read-only towards NSE and Groww; never trades.

- issue [--day D] --live: the day's premium ranges from G13's 3 pm record, run by O1's `premium_ranges` step (a hand
  run writes nothing); it first stores the final seals of earlier issues.
- score: syncs G13's and G13d's files through the verified Drive cache, stores final seals, scores every issue whose
  next session has passed, and writes the report (write-once, with its receipt); commit `receipts/` after.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date

import requests

from ..config import load_app_config
from ..models import now_ist
from ..price_distribution.cli import CACHE_PREFIX as G13_PREFIX
from ..research_data.calendar import CalendarError
from ..storage.owner_token import DriveSignInRefused
from ..storage.raw_store import RawFileConflict
from .constants import ISSUE
from .folders import DATA_AREA, ROOT

STOPPING_FAILURES = (requests.RequestException, DriveSignInRefused, RawFileConflict, RuntimeError, CalendarError,
                     OSError)  # fmt: skip
OWN_PREFIX = f"{DATA_AREA}/{ROOT}"
SYNC_PROBLEMS = "STOPPED: the Drive cache could not verify every file: {problems}"
REPORT_WRITTEN = "report written: {path}"


def add_premrange_parser(subparsers) -> None:
    p = subparsers.add_parser("premrange", help="G13d: next-session 3 pm premium range for each monthly contract")
    p.add_argument("action", choices=("issue", "score"))
    p.add_argument("--day", type=date.fromisoformat, default=None, help="issue: YYYY-MM-DD (default today IST)")
    p.add_argument("--live", action="store_true", help="issue: O1's daily step only (a hand run writes nothing)")
    p.set_defaults(func=cmd_premrange)


def cmd_premrange(args) -> int:
    try:
        return {"issue": _issue, "score": _score}[args.action](args, load_app_config())
    except STOPPING_FAILURES as exc:
        print(f"STOPPED ({type(exc).__name__}): {exc}")
        return 1


def _seal_lines(seals, store, day: date) -> list[str]:
    from ..price_ranges.seals import seal_recent
    from .folders import live_path
    from .wiring import UNDERLYINGS

    return seal_recent(seals, lambda u, d, issue: store.get(live_path(u, d, issue)) is not None, UNDERLYINGS, ISSUE,
                       day)  # fmt: skip


def _issue(args, cfg) -> int:
    from .wiring import build_issuer, build_seals, build_store

    store = build_store()
    seals = build_seals(store)
    issuer = build_issuer(cfg, store, lambda day: _seal_lines(seals, store, day))
    code, lines = issuer.issue(args.day or now_ist().date(), live=args.live)
    print("\n".join(lines))
    return code


def _score(args, cfg) -> int:
    from ..storage.data_wiring import build_drive_cache
    from .folders import scores_path
    from .reader import g13_record, issued_records
    from .report import Issued, score_report, summary_lines
    from .wiring import build_seals, build_store, data_root, method_sha256

    cache = build_drive_cache()
    for prefix in (G13_PREFIX, OWN_PREFIX):
        synced = cache.sync(prefix)
        if not synced.complete:
            print(SYNC_PROBLEMS.format(problems="; ".join(synced.problems)))
            return 1
    store, root, now = build_store(), data_root(), now_ist()
    seals = build_seals(store)
    lines = _seal_lines(seals, store, now.date())
    by_underlying = {}
    for record in issued_records(root):
        day, underlying = date.fromisoformat(record["day"]), record["underlying"]
        nxt = g13_record(root, underlying, date.fromisoformat(record["next_session"]))
        by_underlying.setdefault(underlying, []).append(Issued(record, nxt, seals.seal(underlying, day, ISSUE).late))
    report = score_report(by_underlying, now.date(), method_sha256())
    data = (json.dumps(report, sort_keys=True, indent=1, allow_nan=False) + "\n").encode()
    path = scores_path(now, hashlib.sha256(data).hexdigest())
    store.put(path, data)
    print("\n".join([*lines, *summary_lines(report), REPORT_WRITTEN.format(path=path)]))
    return 0
