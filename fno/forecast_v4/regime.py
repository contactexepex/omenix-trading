"""The scored window's regime, printed beside every v4 verdict (revision 7, judge 98 addendum 6;
`PROTOCOL_v4_calibration.md` section 4).

Inside one regime a verdict measures that regime: the busiest and calmest 2019-26 stretches move every member's claim
and futility rates far from nominal (`research/forecasts/v4_regime_stress.md`). So no claim, "no" or Test A result is
reported without its window's mean closing India VIX, its count of 2% days and its 2%-day band. The inputs are
outcome-side only: the closing VIX and the NIFTY log return of each scored outcome's first session.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .confirmatory import event_band
from .terms import BIG_MOVE


@dataclass(frozen=True)
class WindowRegime:
    mean_vix: float
    big_days: int
    band: tuple[int, int | None] | None  # None: below the 5-day gate (no member judgeable)

    def line(self) -> str:
        return (
            f"scored window regime: mean India VIX {self.mean_vix:.1f}, {self.big_days} 2% days, "
            f"band {_band_name(self.band)}"
        )


def is_big_move(log_return: float) -> bool:
    """A 2% day: the one definition the regime's count and the miss rule's 2% days share (revision 9)."""
    return abs(log_return) >= BIG_MOVE


def window_regime(vix_closes: Sequence[float], log_returns: Sequence[float]) -> WindowRegime:
    """One entry per scored outcome, both lists in the same order."""
    if not vix_closes or len(vix_closes) != len(log_returns):
        raise ValueError("a regime needs one VIX close and one log return per scored outcome")
    big_days = sum(is_big_move(r) for r in log_returns)
    return WindowRegime(sum(vix_closes) / len(vix_closes), big_days, event_band(big_days))


def _band_name(band: tuple[int, int | None] | None) -> str:
    if band is None:
        return "below 5 (not judgeable: undecided)"
    low, high = band
    return f"{low}-{high}" if high is not None else f"{low}+"
