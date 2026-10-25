"""The random-strategy control (story S6 section 6; S1 `random_control`). For each completed position, each of 1,000
runs draws a twin: the same entry and exit sessions, expiry, units and shape; a random direction (a flip mirrors every
leg about the first strike and swaps calls and puts: PCS<->CCS, CDS<->PDS, LC<->LP); and a random first strike within
10 strike steps of the money. It is valued by E4's pricing with C1's charges. A draw that is not quotable at both ends,
breaks the per-trade maximum-loss cap, or the bucket cap given that run's open twins, is redrawn up to 20 times. The
book's percentile among the runs (ties count half) of closed-trade net per rupee-day of risk measures selection luck
only, on the same dates (not window luck); descriptive, never a gate and never in Holm."""

from __future__ import annotations

import random
import statistics
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date

from ..accounting.ledgers import Order
from ..constants import OPTION_CALL, OPTION_PUT
from ..desk.pricing import DeskLeg, price_leg
from ..desk.snapshot import ExecutionSnapshot
from ..research_engine.structures import Leg
from ..risk.inputs import RiskInputError
from ..risk.open_risk import HeldMaxLoss
from .standard_unit import cash

FLIPS = {"PCS": "CCS", "CCS": "PCS", "CDS": "PDS", "PDS": "CDS", "LC": "LP", "LP": "LC"}
RUNS, SEED, WINDOW_STEPS, REDRAWS, MISSING_CAP = 1000, 20261014, 10, 20, 0.10
LABEL = "feasible-random selection on the same dates (selection luck, not window luck); descriptive, never a gate"
UNQUOTABLE, OVER_CAP, NO_MAX_LOSS, BUCKET_FULL = (
    "not quotable at entry and exit", "over the per-trade cap", "maximum loss unknown", "bucket full",
)  # fmt: skip


@dataclass(frozen=True)
class RealTrade:
    structure: str
    legs: tuple[DeskLeg, ...]
    units: int
    entry: date
    exit: date
    net: float
    max_loss: float
    held: int  # sessions held at close (S2's risk-days basis)


@dataclass(frozen=True)
class Twin:
    net: float
    max_loss: float
    sides: tuple[str, ...]


def measure(nets: Sequence[float], risks: Sequence[float]) -> float | None:
    return sum(nets) / sum(risks) if sum(risks) > 0 else None


def mirrored(legs: Sequence[DeskLeg]) -> list[DeskLeg]:
    """The opposite direction: each leg reflected about the first strike, calls and puts swapped, sides kept."""
    pivot, swap = legs[0].leg.strike, {OPTION_CALL: OPTION_PUT, OPTION_PUT: OPTION_CALL}
    return [replace(leg, leg=Leg(2 * pivot - leg.leg.strike, swap[leg.leg.kind], leg.leg.side)) for leg in legs]


def shifted(legs: Sequence[DeskLeg], offset: float) -> list[DeskLeg]:
    return [replace(leg, contract="", leg=Leg(leg.leg.strike + offset, leg.leg.kind, leg.leg.side)) for leg in legs]


def window(snapshot: ExecutionSnapshot, expiry: date, include: float) -> list[float]:
    """The listed strikes within 10 steps of the money (where call and put mids are closest), widened to `include`."""
    strikes = sorted({k for (e, k, _), q in snapshot.quotes.items() if e == expiry})
    pairs = [k for k in strikes if _mid(snapshot, expiry, k, OPTION_CALL) and _mid(snapshot, expiry, k, OPTION_PUT)]
    if not pairs:
        return [include]
    atm = min(pairs, key=lambda k: abs(_mid(snapshot, expiry, k, OPTION_CALL) - _mid(snapshot, expiry, k, OPTION_PUT)))
    step = min((b - a for a, b in zip(strikes, strikes[1:], strict=False)), default=0.0) or 1.0
    near = [k for k in strikes if abs(k - atm) <= WINDOW_STEPS * step]
    return sorted({*near, *(k for k in strikes if min(include, atm) <= k <= max(include, atm))})


def _mid(snapshot: ExecutionSnapshot, expiry: date, strike: float, kind: str) -> float | None:
    quote = snapshot.quote(expiry, strike, kind)
    return (quote.bid + quote.ask) / 2 if quote and not quote.a4_problem else None


class RandomControl:
    def __init__(self, snapshots: Callable[[date], ExecutionSnapshot | None], held: HeldMaxLoss,
                 charges: Mapping[str, float], cap_rs: float, bucket_cap_rs: float,
                 bucket_sides: Mapping[str, Sequence[str]], runs: int = RUNS, seed: int = SEED):  # fmt: skip
        self.snapshots, self.held, self.charges = snapshots, held, dict(charges)
        self.cap_rs, self.bucket_cap_rs, self.runs, self.seed = cap_rs, bucket_cap_rs, runs, seed
        self.sides = {code: (s,) if isinstance(s, str) else tuple(s) for code, s in bucket_sides.items()}
        self._windows: dict[tuple, list[float]] = {}

    def control(self, trades: Sequence[RealTrade]) -> dict:
        trades = sorted(trades, key=lambda t: (t.entry, t.exit))
        book = measure([t.net for t in trades], [self._own_risk(t) * t.held for t in trades])
        if book is None:
            return {"label": LABEL, "percentile": None, "reason": "no completed position"}
        rng, values, missing = random.Random(self.seed), [], 0
        self._seen = {"flipped": 0, "accepted": 0, "rejected": Counter()}
        for _ in range(self.runs):
            nets, risks, open_twins = [], [], []
            for trade in trades:
                twin = self._twin(trade, rng, [(e, t) for e, t in open_twins if e > trade.entry])
                if twin is None:
                    missing += 1
                    continue
                open_twins.append((trade.exit, twin))
                nets.append(twin.net)
                risks.append(twin.max_loss * trade.held)
            values.append(measure(nets, risks))
        share = missing / (self.runs * len(trades))
        found = [v for v in values if v is not None]
        if share > MISSING_CAP or not found:
            return {"label": LABEL, "percentile": None, "missing_share": round(share, 6),
                    "rejected_draws": dict(sorted(self._seen["rejected"].items())),
                    "reason": f"not computable: {missing} twins missing"}  # fmt: skip
        below, ties = sum(v < book for v in found), sum(v == book for v in found)
        seen = self._seen
        return {"label": LABEL, "runs": len(found), "book_measure": round(book, 6),
                "percentile": round((below + ties / 2) / len(found), 6),
                "runs_median": round(statistics.median(found), 6), "missing_twins": missing,
                "missing_share": round(share, 6), "reason": "",
                "flipped_share": round(seen["flipped"] / seen["accepted"], 6) if seen["accepted"] else None,
                "rejected_draws": dict(sorted(seen["rejected"].items()))}  # fmt: skip

    def _twin(self, trade: RealTrade, rng: random.Random, open_twins: list) -> Twin | None:
        entry, leave = self.snapshots(trade.entry), self.snapshots(trade.exit)
        if entry is None or leave is None:
            return None
        for _ in range(REDRAWS):
            flip = trade.structure in FLIPS and rng.random() < 0.5
            legs, code = (mirrored(trade.legs), FLIPS[trade.structure]) if flip else (list(trade.legs), trade.structure)
            key = (trade.entry, legs[0].expiry, legs[0].leg.strike)
            strikes = self._windows.setdefault(key, window(entry, *key[1:]))
            twin = self._valued(shifted(legs, rng.choice(strikes) - legs[0].leg.strike), code, trade, entry, leave)
            if isinstance(twin, Twin) and not self._bucket_room(twin, open_twins):
                twin = BUCKET_FULL
            if isinstance(twin, Twin):
                self._seen["accepted"] += 1
                self._seen["flipped"] += flip
                return twin
            self._seen["rejected"][twin] += 1  # each redraw's reason, disclosed (review 120)
        return None

    def _valued(self, legs, code, trade: RealTrade, entry, leave) -> Twin | str:
        """The twin, or why it cannot be one."""
        opening = [price_leg(entry, leg, leg.side(True), trade.units) for leg in legs]
        closing = [price_leg(leave, leg, leg.side(False), trade.units) for leg in legs]
        if not all(q.fills for q in (*opening, *closing)):
            return UNQUOTABLE
        flow_in = sum(cash(Order(q.side, q.price, trade.units), self.charges) for q in opening)
        try:
            max_loss = self.held.of_legs([(leg.leg, trade.units) for leg in legs], flow_in)
        except RiskInputError:
            return NO_MAX_LOSS
        if max_loss > self.cap_rs:
            return OVER_CAP
        net = flow_in + sum(cash(Order(q.side, q.price, trade.units), self.charges) for q in closing)
        return Twin(net, max_loss, self.sides.get(code, ()))

    def _own_risk(self, trade: RealTrade) -> float:
        """The real trade's maximum loss on its twins' basis (B2's model on its legs at the entry snapshot's touch), so
        the trade ties its own twin; the record's figure (priced at the pack's mids) only when it cannot be priced."""
        entry = self.snapshots(trade.entry)
        quotes = [price_leg(entry, leg, leg.side(True), trade.units) for leg in trade.legs] if entry else []
        if not quotes or not all(q.fills for q in quotes):
            return trade.max_loss
        flow = sum(cash(Order(q.side, q.price, trade.units), self.charges) for q in quotes)
        try:
            return self.held.of_legs([(leg.leg, trade.units) for leg in trade.legs], flow)
        except RiskInputError:
            return trade.max_loss

    def _bucket_room(self, twin: Twin, open_twins: list) -> bool:
        for side in twin.sides:
            used = sum(t.max_loss for _, t in open_twins if side in t.sides)
            if used + twin.max_loss > self.bucket_cap_rs:
                return False
        return True
