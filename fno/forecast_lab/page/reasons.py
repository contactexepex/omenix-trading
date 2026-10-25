"""Why a recent forecast missed (stories FL1-1c v4 and FL1-1d): for each of the last 30 sessions (the page's window;
the designer's "when it was wrong" table) whose close fell outside "almost
certainly", how far outside, and the likely reasons, after the fact, from facts we already hold. They are never
guessed: a reason appears only when its fact crosses its threshold, else "no clear reason in our data".
Facts used: India VIX (the NIFTY panel's daily VIX), scheduled events (research/data/events), NIFTY's F&O expiry
days (the options panel), Brent and USD/INR (A17's public tables), FII/DII cash flows (P8's archive, from 13 Oct
2026; owner, 21 Oct 2026). Not checked yet, and said so on the page (`UNCHECKED`): global markets (the owner wants
Asia, GIFT Nifty and the US together, not the US alone; a data story adds them) and the opening gap (no index open
price is held)."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date

from .model import Miss, Outcome

SESSIONS = 30  # the page's 30-session window (FL1-1d; was 7 in FL1-1c)
VIX_JUMP = 0.10  # India VIX up 10% or more on the day
OIL_MOVE = 0.03  # Brent moved 3% or more in the last print before the day
FX_MOVE = 0.005  # USD/INR moved 0.5% or more in the last print before the day
BIG_FLOW = 4000.0  # Rs crore: an FII or DII net cash flow this large on the day (reasoning only: a typical day's net
# is a few hundred to about 3,000 crore)
UNCHECKED = ("global markets (Asia, GIFT Nifty, US)", "the opening gap")
NO_REASON = "no clear reason in our data"


@dataclass(frozen=True)
class Facts:
    vix: Mapping[date, float] = field(default_factory=dict)
    events: Mapping[date, str] = field(default_factory=dict)
    expiries: frozenset[date] = frozenset()
    brent: Mapping[date, float] = field(default_factory=dict)
    usdinr: Mapping[date, float] = field(default_factory=dict)
    flows: Mapping[date, tuple[float, float]] = field(default_factory=dict)  # (FII net, DII net), Rs crore


def _last_move(series: Mapping[date, float], day: date) -> float | None:
    """The change between the last two prints before `day`, as a share."""
    before = sorted(d for d in series if d < day)[-2:]
    if len(before) < 2 or not series[before[0]]:
        return None
    return series[before[1]] / series[before[0]] - 1


def reasons(day: date, previous: date, facts: Facts, above: bool) -> tuple[str, ...]:
    """`above`: the close was above the range. A flow counts only when it pushes that way (net buying for a close
    above, net selling for one below): a fact pushing against the miss is no reason for it."""
    found = []
    vix_now, vix_before = facts.vix.get(day), facts.vix.get(previous)
    if vix_now and vix_before and vix_now / vix_before - 1 >= VIX_JUMP:
        found.append(f"India VIX jumped from {vix_before:.1f} to {vix_now:.1f}")
    found += [f"scheduled event: {what}" for when, what in sorted(facts.events.items()) if previous < when <= day]
    if day in facts.expiries:
        found.append("NIFTY F&O expiry day")
    for name, series, limit in (("Brent oil", facts.brent, OIL_MOVE), ("the rupee (USD/INR)", facts.usdinr, FX_MOVE)):
        move = _last_move(series, day)
        if move is not None and abs(move) >= limit:
            found.append(f"{name} moved {move:+.1%} just before")
    found += _flows(facts.flows.get(day), above)
    return tuple(found) or (NO_REASON,)


def _flows(nets: tuple[float, float] | None, above: bool) -> list[str]:
    if nets is None:
        return []
    return [f"{who} {'bought' if net > 0 else 'sold'} a net Rs {abs(net):,.0f} crore that day"
            for who, net in zip(("FIIs", "DIIs"), nets, strict=True)
            if abs(net) >= BIG_FLOW and (net > 0) == above]  # fmt: skip


def recent_misses(points: Sequence[Outcome], previous: Callable[[date], date], facts: Facts) -> tuple[Miss, ...]:
    out = []
    for point in reversed(points[-SESSIONS:]):
        if point.inside_90:
            continue
        above = point.close > point.band.q95
        gap = point.close - point.band.q95 if above else point.band.q05 - point.close
        found = reasons(point.day, previous(point.day), facts, above)
        out.append(Miss(point.day, "above" if above else "below", gap, found))
    return tuple(out)
