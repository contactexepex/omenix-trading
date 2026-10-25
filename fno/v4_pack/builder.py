"""The v4 pack from the day's capture (story G10 part 2, sections 1 and 3). Only a capture whose two clock readings
were both `clock_ok` can give an `A` pack; a field received outside 14:30:00-14:40:00 IST is not in it; a required
field missing (spot, the future of `e`, India VIX, `e`'s ATM call and put, IV30) gives no pack: the day is
`system_late`, with the reasons named. IV30 is G1 v2's live rule unchanged (B7's ATM mids on Black-76, then
`interpolate_30d`), on the rows inside the window only."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime

from ..constants import OPTION_CALL, OPTION_PUT, V4_DAY_A
from ..forecast.iv30 import interpolate_30d
from ..forecast.live_pack import NSE_TIME_FORMATS
from ..intraday.clock import CLOCK_OK
from ..models import IST
from ..quotes.v4_extras import FUTURE_KIND
from ..research_data.panel_reader import FutureQuote as PanelFuture
from ..research_data.quote_snapshots import CutoffSnapshot, LiveQuote
from ..research_engine.live_features import LiveAtmIvMinusRealised
from .capture import V4Capture
from .codec import capture_window
from .model import ChainQuote, FutureQuote, Iv30, Level, Pack, VixLevel

SOURCE = "a4e_named_window_v4"


@dataclass(frozen=True)
class Built:
    pack: Pack | None  # None: the day is system_late
    reasons: tuple[str, ...]  # why there is no pack (empty when there is one)
    notes: tuple[str, ...] = ()  # what the release alerts beside its label (a V4 expiry the capture could not choose)


def late(*reasons: str) -> Built:
    return Built(None, reasons)


class PackBuilder:
    def __init__(self, iv_rule: LiveAtmIvMinusRealised, iv_method: str, clock: Callable[[], datetime]):
        self.iv_rule, self.iv_method, self.clock = iv_rule, iv_method, clock

    def build(self, day: date, capture: V4Capture | None) -> Built:
        if capture is None:
            return late("no canonical v4 capture")
        meta = capture.meta
        if meta.get("clock_status") != CLOCK_OK:
            return late(f"clock not checked ok ({meta.get('clock_status') or 'missing'})")
        start, end = capture_window(day)
        inside = lambda moment: moment is not None and start <= moment <= end  # noqa: E731
        expiry = min((f for f in _futures(meta) if f[0] > day), default=None, key=lambda f: f[0])
        levels_at = _time(meta.get("levels_received_at"))
        chain_at = {c["expiry"]: (c.get("spot"), _time(c.get("response_received_at"))) for c in meta.get("chains", [])}
        spot, spot_at = chain_at.get(expiry[0].isoformat(), (None, None)) if expiry else (None, None)
        missing = [reason for reason, absent in (
            ("no monthly future after the day", expiry is None),
            ("the levels (India VIX, futures) were not received in the window", not inside(levels_at)),
            ("no India VIX", meta.get("india_vix") is None),
            ("no spot from e's chain in the window", spot is None or not inside(spot_at)),
        ) if absent]  # fmt: skip
        if missing:
            return late(*missing)
        valid = [r for r in capture.rows if r.get("valid") == "true" and inside(_time(r["response_received_at"]))]
        quotes = tuple(_quote(r) for r in valid if r["type"] in (OPTION_CALL, OPTION_PUT))
        if not _has_atm_pair(quotes, expiry[0], float(spot)):
            return late("no valid ATM call and put of e in the window")
        iv30 = self._iv30(day, float(spot), float(meta["india_vix"]), quotes, _futures(meta), levels_at)
        if iv30 is None:
            return late("IV30 not computable from the window's quotes")
        future = _future(expiry, levels_at, _future_row(capture.rows, expiry[0], inside))
        vix = VixLevel(float(meta["india_vix"]), levels_at, _nse_time(str(meta.get("india_vix_time", ""))))
        pack = Pack(day, V4_DAY_A, SOURCE, meta.get("provider") or "groww", f"{capture.dataset}/{capture.snapshot_id}",
                    self.clock(), Level(float(spot), spot_at), future, vix, quotes, iv30,
                    _date(meta.get("v4_expiry")))  # fmt: skip
        return Built(pack, (), tuple(note for note in (meta.get("v4_expiry_note"),) if note))

    def _iv30(self, day, spot, vix, quotes, futures, levels_at) -> Iv30 | None:
        live = tuple(LiveQuote(q.expiry, q.strike, q.kind, q.bid, q.ask, True) for q in quotes)
        listed = tuple(PanelFuture(e, last, 0.0, volume, 0) for e, last, volume in futures)
        snapshot = CutoffSnapshot(day, levels_at.replace(tzinfo=None), spot, vix, live, listed)
        ivs = {e: self.iv_rule.atm_implied_vol_points(snapshot, e) for e, *_ in sorted(futures) if e >= day}
        found = interpolate_30d(day, ivs)
        if found is None:
            return None
        used = [q.observed_at for q in quotes if q.expiry in found.expiries]
        return Iv30(found.points, found.flagged, found.expiries, self.iv_method, max([*used, levels_at]))


def _futures(meta: dict) -> list[tuple[date, float, int]]:
    """(expiry, last, volume): Black-76 prices only on a future that traded (B7), as G1 v2's live pack passes it."""
    return [(date.fromisoformat(f["expiry"]), float(f["last"]), int(f.get("volume") or 0))
            for f in meta.get("futures", []) if f.get("last")]  # fmt: skip


def _quote(row: dict) -> ChainQuote:
    return ChainQuote(date.fromisoformat(row["expiry"]), float(row["strike"]), row["type"], _number(row["bid"]),
                      _number(row["ask"]), _number(row["last"]), _time(row.get("last_trade_time")),
                      _time(row["response_received_at"]))  # fmt: skip


def _has_atm_pair(quotes: tuple[ChainQuote, ...], expiry: date, spot: float) -> bool:
    """`e`'s ATM strike (nearest the spot, a tie to the lower, B7's rule) has a two-sided call and put."""
    legs = [q for q in quotes if q.expiry == expiry]
    if not legs:
        return False
    strike = min({q.strike for q in legs}, key=lambda k: (abs(k - spot), k))
    sides = {q.kind for q in legs if q.strike == strike and q.mid is not None}
    return sides == {OPTION_CALL, OPTION_PUT}


def _time(text: str | None) -> datetime | None:
    if not text:
        return None
    found = datetime.fromisoformat(text)
    return found if found.tzinfo is not None else None


def _nse_time(text: str) -> datetime | None:
    for pattern in NSE_TIME_FORMATS:
        try:
            return datetime.strptime(text, pattern).replace(tzinfo=IST)
        except ValueError:
            continue
    return None


def _number(text: str | None) -> float | None:
    return float(text) if text else None


def _future_row(rows: tuple[dict, ...], expiry: date, inside) -> dict | None:
    """The capture's own quote of `e`'s future (A4e's `FUT` row), received inside the window; None when none came."""
    found = [r for r in rows if r["type"] == FUTURE_KIND and r["expiry"] == expiry.isoformat()
             and inside(_time(r["response_received_at"]))]  # fmt: skip
    return found[0] if found else None


def _future(expiry: tuple[date, float, int], levels_at: datetime, row: dict | None) -> FutureQuote:
    """NSE's last and day volume at the level read; the quote's bid, ask and last trade time at its own answer time."""
    if row is None:
        return FutureQuote(expiry[0], expiry[1], None, None, levels_at, None, expiry[2])
    return FutureQuote(expiry[0], expiry[1], _number(row["bid"]), _number(row["ask"]), levels_at,
                       _time(row.get("last_trade_time")), expiry[2], _time(row["response_received_at"]))  # fmt: skip


def _date(text: str | None) -> date | None:
    return date.fromisoformat(text) if text else None
