"""What each live capture run also settles (story G7b completion, parts c and b2):

- V5's pending outcomes: every stored V5 term whose expiry's F&O file is now archived is resolved once and written
  write-once (`v4/outcomes/v5/...`, with its source, SHA-256 and first-seen time); a refused level is printed, an
  unresolved one waits. This runs before the day's rows, so V5's base rate counts every outcome first seen before `d`.
- The proxy-drift pairs: each live day's pack IV30 beside the same day's end-of-day IV30 proxy, written once the EOD
  chain exists (`v4/diagnostics/proxy_drift/...`), for G8's drift line (protocol 3.1, `diagnostics.proxy_drift`).
- W8's review trigger (judge 591 m2): when the median back-filled / live `RV_s` ratio over the latest 20 paired live
  days leaves [0.95, 1.05], one alert to #fno-desk and a write-once marker (`v4/diagnostics/w8_review/...`), so it is
  raised once; the owner's row decides what follows.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import date

from ..forecast_v4.diagnostics import RECENT_DAYS, proxy_drift
from ..forecast_v4.settlement import V5Outcome
from .implied import IvPoint
from .option_history import OptionHistory, outcome_bytes, outcome_path
from .option_outcomes import Refused
from .option_terms import OptionTerms

DRIFT_FOLDER = "v4/diagnostics/proxy_drift"
RESOLVED = "V5 {day}: outcome written ({inside}), first seen {seen}"
REFUSED = "V5 {day}: settlement refused, the outcome stays unresolved: {reason}"
W8_REVIEW_FOLDER = "v4/diagnostics/w8_review"
W8_BAND = (0.95, 1.05)  # the latest RECENT_DAYS (20) paired days' median
W8_ALERT = ("v4 W8 review {day}: back-filled candle RV_s / live A16 RV_s, median {median:.4f} over the latest 20 "
            "paired live days, is outside [0.95, 1.05]: an owner row is due (keep W8, correct yardstick A's window by "
            "the factor, or drop it)")  # fmt: skip


def drift_path(day: date) -> str:
    return f"{DRIFT_FOLDER}/{day:%Y}/{day.isoformat()}.json"


def drift_bytes(day: date, pack: IvPoint | None, eod: IvPoint | None) -> bytes:
    """A flagged side is kept with its flag; the drift line pairs unflagged values only."""
    doc = {"day": day.isoformat(), **_side("pack", pack), **_side("eod", eod)}
    return json.dumps(doc, sort_keys=True).encode("utf-8")


def _side(name: str, iv: IvPoint | None) -> dict:
    return {f"{name}_iv30": None if iv is None else iv.value, f"{name}_flagged": None if iv is None else iv.flagged}


def drift_pair(data: bytes) -> tuple[date, float | None, float | None]:
    """A stored pair as `diagnostics.proxy_drift` reads it: a flagged or missing side is no value."""
    doc = json.loads(data)
    pack = None if doc["pack_flagged"] in (None, True) else doc["pack_iv30"]
    eod = None if doc["eod_flagged"] in (None, True) else doc["eod_iv30"]
    return date.fromisoformat(doc["day"]), pack, eod


def resolve_pending_v5(history: OptionHistory, resolve: Callable[[OptionTerms], V5Outcome | Refused | None],
                       put: Callable[[str, bytes], None]) -> tuple[list[str], dict[date, V5Outcome]]:  # fmt: skip
    """The printed lines and the outcomes written now (the capture's V5 base rate reads them the same run)."""
    lines, written = [], {}
    for terms in history.pending_v5():
        found = resolve(terms)
        if isinstance(found, Refused):
            lines.append(REFUSED.format(day=terms.day, reason=found.reason))
        elif found is not None:
            put(outcome_path(terms.day), outcome_bytes(terms.day, found))
            written[terms.day] = found
            lines.append(RESOLVED.format(day=terms.day, inside="inside" if found.inside else "outside",
                                         seen=found.first_seen_at.isoformat()))  # fmt: skip
    return lines, written


def write_drift_pairs(packs: Mapping[date, IvPoint | None], eod: Mapping[date, IvPoint], written: set[date],
                      put: Callable[[str, bytes], None]) -> list[date]:  # fmt: skip
    """`packs`: each released (A) day's pack IV30; `eod`: the EOD proxy by day; `written`: days already paired. A
    day waits until its EOD chain is archived; returns the days written now."""
    done = []
    for day in sorted(set(packs) - written):
        if day in eod:
            put(drift_path(day), drift_bytes(day, packs[day], eod[day]))
            done.append(day)
    return done


def review_w8(day: date, pairs, raised: bool, put: Callable[[str, bytes], None],
              send: Callable[[str], str]) -> list[str]:  # fmt: skip
    """`raised`: a marker already exists (the trigger fired before); fewer than 20 paired days raise nothing."""
    drift = proxy_drift(pairs)
    median = drift.recent_median_ratio
    if raised or drift.pairs < RECENT_DAYS or W8_BAND[0] <= median <= W8_BAND[1]:
        return []
    text = W8_ALERT.format(day=day, median=median)
    document = {"day": day.isoformat(), "median_latest_20": median, "pairs": drift.pairs}
    put(f"{W8_REVIEW_FOLDER}/{day.isoformat()}.json", json.dumps(document, sort_keys=True).encode("utf-8"))
    return [text, send(text)]
