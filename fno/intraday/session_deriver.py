"""One session's candle-close row (story A16b) from its archived inputs: the 15-minute window copy, the session's
1-minute copy (when it has any candle), NSE's day and the previous session's 15:30 level. Pure: no fetch, no write, so
the back-fill and `backfill-verify` give the same row from the same copies.

Void reasons, all listed: `missing_candles:N` (the present levels are still checked, decision 62), `no_1m_check:N` (a
received 1-minute answer lacks N minutes that present levels need), `candle_mismatch:<marks>`, `nse_unchecked` (NSE has
no file for the day), `outside_nse_range`. Any reason but `missing_candles` makes the levels untrusted, so no figure is
computed; with `missing_candles` only, the parts whose levels exist are computed, as A16 does."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from ..global_cues.table import provenance
from .candle_archive import ArchivedCopy
from .candle_levels import SessionCandles, parse_candles, session_candles
from .document import utc_text
from .minute_check import check_minutes
from .nse_days import NseReading
from .nse_range import check_range
from .realised_vol import IntradayRealisedVol
from .session_rv import OK, VOID, figure
from .slots import marks

SOURCE = "groww_candles"
CHECKED, UNCHECKED = "checked", "unchecked"
NO_PREVIOUS = "no_previous_close"  # no usable 15:30 level for the previous session
TRUSTED_LAST_LEVEL = ("missing_candles",)  # a void session whose 15:30 level may still start the next overnight return


@dataclass(frozen=True)
class SessionInputs:
    session: date
    window: ArchivedCopy
    minutes: ArchivedCopy | None  # None when the session has no candle at all (nothing to check)
    nse: NseReading
    previous_close: float | None


class SessionDeriver:
    def __init__(self, strategy: IntradayRealisedVol, next_session: Callable[[date], date]):
        self.strategy, self.next_session = strategy, next_session

    def candles(self, session: date, window: ArchivedCopy) -> SessionCandles:
        return session_candles(session, parse_candles(window.rows))

    def derive(self, given: SessionInputs) -> dict:
        found = self.candles(given.session, given.window)
        reasons = [f"missing_candles:{found.missing}"] if found.missing else []
        minutes = (
            check_minutes(given.session, found.levels, parse_candles(given.minutes.rows)) if given.minutes else None
        )
        present = sum(level is not None for level in found.levels)
        if present and minutes is None:  # never a present level without its check (no silent fall-back)
            reasons.append(f"no_1m_check:{present}")
        if minutes and minutes.missing:
            reasons.append(f"no_1m_check:{len(minutes.missing)}")
        if minutes and minutes.mismatched:
            reasons.append(f"candle_mismatch:{'+'.join(minutes.mismatched)}")
        gaps = None
        if given.nse.day is None:
            reasons.append("nse_unchecked")
        else:
            gaps = check_range(found.levels, found.used, given.nse.day, minutes.pre_open_close if minutes else None)
            reasons += ["outside_nse_range"] if gaps.outside else []
        trusted = all(r.split(":")[0] in TRUSTED_LAST_LEVEL for r in reasons)
        result = self.strategy.compute(list(found.levels), given.previous_close) if trusted else None
        if result is not None and result.previous_close_missing:
            reasons.append(NO_PREVIOUS)
        return self._row(given, found, result, reasons, gaps)

    def last_level(self, row: dict, window: ArchivedCopy) -> float | None:
        """A written session's 15:30 level for the next overnight return; None when its levels are untrusted."""
        reasons = [r for r in row["void_reason"].split("; ") if r and r != NO_PREVIOUS]
        if not all(r.split(":")[0] in TRUSTED_LAST_LEVEL for r in reasons):
            return None
        return self.candles(date.fromisoformat(row["session"]), window).levels[-1]

    def _row(self, given: SessionInputs, found: SessionCandles, result, reasons: list[str], gaps) -> dict:
        session_marks = marks(given.session)
        copies = [given.window] + ([given.minutes] if given.minutes else [])
        first_seen = max(c.fetched_at for c in copies)
        shas = [c.sha256 for c in copies] + [given.nse.sha256]
        figures = (result.session, result.intraday, result.overnight) if result else (None, None, None)
        return {
            "session": given.session.isoformat(), "status": VOID if reasons else OK,
            "rv_session": figure(figures[0]), "rv_intraday": figure(figures[1]), "rv_overnight": figure(figures[2]),
            "vol_pct": "" if not result or result.vol_pct is None else f"{result.vol_pct:.4f}",
            "void_reason": "; ".join(reasons), "good_slots": sum(v is not None for v in found.levels),
            "due_slots": len(session_marks), "basis_counts": found.basis_counts,
            "measure": self.strategy.measure, "method": self.strategy.method, "source": SOURCE,
            "as_of": utc_text(session_marks[-1]), "first_seen_at": utc_text(first_seen),
            "inputs_sha256": hashlib.sha256("\n".join(shas).encode()).hexdigest(),
            "provenance": provenance(given.session, first_seen, self.next_session),
            "nse_check": UNCHECKED if given.nse.day is None else CHECKED,
            "nse_open_gap": _gap(gaps and gaps.open_gap), "nse_high_gap": _gap(gaps and gaps.high_gap),
            "nse_low_gap": _gap(gaps and gaps.low_gap), "outside_candles": found.outside,
            "copy_15m": given.window.path, "copy_1m": given.minutes.path if given.minutes else "",
        }  # fmt: skip


def _gap(value: float | None) -> str:
    return "" if value is None else f"{value:.2f}"
