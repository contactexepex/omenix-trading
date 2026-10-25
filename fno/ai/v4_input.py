"""Story G11, the AI books' v4 input (response 272): what one book is given to answer the day's v4 questions, built on
the Actions side from the released pack (read through the verified Drive cache at the release record's SHA, story O9)
and the official closes before the day. A routine session has no Drive credentials (F1t's rule), so this input
travels in the book's pointer; `input_sha256` (canonical JSON) ties the answer to exactly this input. The fire logs
that hash with the answer labels and Hybrid's envelope, and the collection judges against the log; it never rebuilds
the input, whose source files can still change after the fire.

- **The pack, summarised:** spot, the near future, India VIX, IV30 (with its single-expiry flag) and, per expiry, the
  ATM call and put mids and their straddle; the chain within +-5% of spot for the nearest expiry. Never a raw broker
  row beyond those quotes.
- **The closes** of the last 260 sessions and the same derived facts as v2, with the pack's 14:30 spot standing for
  today (`export.py`'s own helpers, reused).
- **Each point question's history in its own measure** (protocol 1.1; G11 C4): V1 the intraday `RV_s` of A16's
  committed sessions before the day (a void session shown as void, never filled), V2 the `close_proxy` `RV_s` of the
  regular sessions before it, from the official closes; nothing dated the day itself.
- **Hybrid only:** per question, the rules slot's own value (under its forecaster's name) and the primary baseline's
  (`primary_baseline`, the series G8 uses that day, V1's one-way switch to HAR intraday included), both committed
  before the 14:30 cutoff, and the envelope spanning them (`Envelope.span`; Book 3 sees no rule's answer).
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from ..v4_pack.model import ChainQuote, Pack
from .envelope import Envelope
from .export import RV_RETURNS, canonical, realised_vol_points

NEAR_SPOT = 0.05  # the chain's strikes shown: within 5% of spot, nearest expiry only
CE, PE = "CE", "PE"
PRIMARY = "primary_baseline"  # Hybrid's input names the primary baseline's value under this key (its name can change)

Rules = Mapping[str, Mapping[str, float | None]]  # question -> forecaster -> its value (None: no forecast)
History = Mapping[str, Mapping[str, list]]  # point question -> {"dates": [...], "rv_s": [... or None]}, oldest first
CHAIN_COLUMNS = ["strike", "kind", "bid", "ask", "last"]  # the chain as rows of columns: the pointer is retyped by the
# routine's model into `brief`, so no key is repeated per row (review of dfb26381: 33 KB as dicts, about half as rows)


@dataclass(frozen=True)
class V4InputFor:
    """Who the input is for: the book, its registered version and the day's questions (the rules slot's)."""

    book: str
    version: str
    day: date
    questions: Sequence[str]
    pack_sha256: str


def build_v4_input(who: V4InputFor, pack: Pack, closes: Sequence[tuple[str, float, float]], rules: Rules | None,
                   widths: tuple[float, float] | None, history: History) -> dict:  # fmt: skip
    """The book's input; `rules` and `widths` (probability, point) are Hybrid's only (both or neither)."""
    if (rules is None) != (widths is None):
        raise ValueError(f"{who.book}: rules belong to Hybrid's input only")
    if pack.day != who.day:
        raise ValueError(f"the pack is for {pack.day}, the input for {who.day}")
    built = {
        "book": who.book,
        "day": who.day.isoformat(),
        "version": who.version,
        "questions": list(who.questions),
        "pack_sha256": who.pack_sha256,
        "pack": pack_summary(pack),
        "closes_before_day": {
            "dates": [c[0] for c in closes],
            "nifty": [c[1] for c in closes],
            "vix": [c[2] for c in closes],
        },  # fmt: skip
        "derived": derived_facts(pack, closes),
        "history": {q: {"dates": list(h["dates"]), "rv_s": list(h["rv_s"])} for q, h in sorted(history.items())},
    }
    if rules is not None:
        asked = {q: dict(rules.get(q, {})) for q in who.questions}
        spans = {q: [v for v in asked[q].values() if v is not None] for q in who.questions}
        built["rules"] = {"by_question": asked, "envelope": Envelope.span(spans, *widths).as_json()}
    return built


def input_sha256(built: dict) -> str:
    return hashlib.sha256(canonical(built)).hexdigest()


def pack_summary(pack: Pack) -> dict:
    expiries = sorted({q.expiry for q in pack.chain})
    return {
        "label": pack.label,
        "released_at": pack.released_at.isoformat(),
        "spot": pack.spot.value,
        "future": {
            "expiry": pack.future.expiry.isoformat(),
            "last": pack.future.last,
            "bid": pack.future.bid,
            "ask": pack.future.ask,
        },  # fmt: skip
        "india_vix": pack.india_vix.value,
        "iv30": {
            "value": pack.iv30.value,
            "single_expiry": pack.iv30.flagged,
            "expiries": [e.isoformat() for e in pack.iv30.expiries],
        },  # fmt: skip
        "atm_by_expiry": [_atm(pack, e) for e in expiries],
        "chain_near_spot": {"columns": CHAIN_COLUMNS, "rows": _near_spot(pack, expiries[0]) if expiries else []},
    }


def derived_facts(pack: Pack, closes: Sequence[tuple[str, float, float]]) -> dict:
    spot, vix = pack.spot.value, pack.india_vix.value
    last = closes[-1] if closes else None
    path = [c[1] for c in closes[-RV_RETURNS:]] + [spot]
    return {
        "trailing_rv20_points_with_1430_spot": realised_vol_points(path),
        "nifty_1430_change_pct_vs_previous_close": (spot / last[1] - 1) * 100 if last else None,
        "vix_1430_change_vs_previous_close": vix - last[2] if last else None,
    }


def _atm(pack: Pack, expiry: date) -> dict:
    quotes = [q for q in pack.chain if q.expiry == expiry]
    strike = min({q.strike for q in quotes}, key=lambda k: (abs(k - pack.spot.value), k))
    call, put = (_mid(quotes, strike, kind) for kind in (CE, PE))
    straddle = call + put if call is not None and put is not None else None
    return {"expiry": expiry.isoformat(), "strike": strike, "call_mid": call, "put_mid": put, "straddle_mid": straddle}


def _mid(quotes: Sequence[ChainQuote], strike: float, kind: str) -> float | None:
    return next((q.mid for q in quotes if q.strike == strike and q.kind == kind), None)


def _near_spot(pack: Pack, expiry: date) -> list[list]:
    low, high = pack.spot.value * (1 - NEAR_SPOT), pack.spot.value * (1 + NEAR_SPOT)
    near = [q for q in pack.chain if q.expiry == expiry and low <= q.strike <= high]
    return [[q.strike, q.kind, q.bid, q.ask, q.last] for q in sorted(near, key=lambda q: (q.strike, q.kind))]
