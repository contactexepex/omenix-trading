"""The 2-4 key points per index (story FL1-1d-2), chosen by a stated order, never by a model:
- the morning ("why this forecast"): what the forecast is built from (the one `used` point), then the day's flags,
  then GIFT Nifty's gap when shown (the one pre-open level; it has no history here to size it against), then the
  other context cues by the size of their move against their own usual moves;
- the evening ("why it was right or wrong"): on a miss, its after-the-fact reasons (FL1-1c's direction-aware facts),
  then the US equity cues that moved the same way as the miss, then the other context cues by size.
Context is never a cause: the page labels it so."""

from __future__ import annotations

from .cues import AVAILABLE, USED, Cue, SectionView
from .model import Outcome

MIN_POINTS, MAX_POINTS = 2, 4
QUIET = "no notable moves in our data"  # said when fewer than 2 points exist (judge 449), never padded with guesses
BUILT_FROM = "Built from"
INPUTS = {
    "implied": "option prices (the range the options imply)",
    "rv20": "the last 20 sessions' moves",
    "hist750": "the last 750 sessions' moves",
    "ewma_t4": "recent moves, the newest weighted most",
    "no_change": "no move from the last level",
}
EQUITIES, GIFT = ("S&P 500", "Nasdaq-100"), "GIFT Nifty"
REASON = "Reason (after the fact)"


def _shown(sections: tuple[SectionView, ...]) -> list[Cue]:
    return [c for s in sections if s.status == AVAILABLE for c in s.items]


def _by_size(cues: list[Cue]) -> list[Cue]:
    return sorted((c for c in cues if c.size is not None), key=lambda c: -c.size)


def morning_points(method: str, sections: tuple[SectionView, ...]) -> tuple[Cue, ...]:
    cues = _shown(sections)
    used = Cue(BUILT_FROM, text=INPUTS.get(method, method), role=USED)
    flags = [c for c in cues if c.text is not None]
    gift = [c for c in cues if c.name == GIFT]
    return (used, *flags, *gift, *_by_size([c for c in cues if c.text is None]))[:MAX_POINTS]


def evening_points(
    today: Outcome | None, reasons: tuple[str, ...], sections: tuple[SectionView, ...]
) -> tuple[Cue, ...]:
    cues = [c for c in _shown(sections) if c.text is None]
    if today is None or today.inside_90:
        moves = _by_size(cues)[: MAX_POINTS - 2]
        return tuple(moves) if len(moves) >= MIN_POINTS else (*moves, Cue(QUIET, text=QUIET))
    up = today.close > today.band.q95
    said = [Cue(REASON, text=r) for r in reasons]
    same_way = [c for c in cues if c.name in EQUITIES and c.change is not None and (c.change > 0) == up]
    rest = [c for c in _by_size(cues) if c not in same_way]
    return (*said, *_by_size(same_way), *rest)[:MAX_POINTS]
