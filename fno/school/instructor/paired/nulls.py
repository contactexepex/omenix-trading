"""The comparison's own checks on fakes (story MS-INS, part d; 325 section 6.2, 327 correction 3): how often a driver
with no edge reaches "watching" (the false-claim rate under shared shocks and overlapping holds), and how many sessions
a planted edge needs to reach it. Both run the real series and status code on simulated road-slots, never on
records."""

import math
import random
from dataclasses import dataclass
from datetime import date, timedelta
from statistics import NormalDist

from ...constants import RoadCode
from ..contracts import Measure
from ..thresholds import BATCH_HOLD_MULTIPLE, MIN_BATCH
from .series import paired_series
from .status import paired_row
from .values import RoadSlot, SlotStatus

ROADS = tuple(RoadCode)
FIRST_SESSION = date(2027, 1, 4)


@dataclass(frozen=True)
class Market:
    """A simulated market: each session's shared shock, how much the roads share it, the hold in sessions and the
    spread of a trade's return on risk around its edge."""

    shared: float = 0.6  # correlation of two roads' outcomes on one session
    hold: int = 10  # sessions: each outcome sums the shocks over its hold, so neighbouring sessions overlap
    spread: float = 0.5  # standard deviation of one trade's return on risk


def simulated_slots(seed: int, sessions: int, edge: float, market: Market | None = None):
    """A driver trading every road every session (return on risk: edge plus shared and own noise) against N0."""
    market, draw = market or Market(), random.Random(seed)
    shocks = [draw.gauss(0, 1) for _ in range(sessions + market.hold)]
    days = [FIRST_SESSION + timedelta(days=i) for i in range(sessions)]
    driver, control = {}, {}
    for i, day in enumerate(days):
        common = sum(shocks[i : i + market.hold]) / market.hold**0.5
        for road in ROADS:
            own = draw.gauss(0, 1)
            ror = edge + market.spread * (market.shared**0.5 * common + (1 - market.shared) ** 0.5 * own)
            driver[(day, road)] = RoadSlot(day, road, "D@1", SlotStatus.CLOSED, ror)
            control[(day, road)] = RoadSlot(day, road, "N0@1", SlotStatus.ABSTAINED)
    return driver, control


@dataclass(frozen=True)
class SellerShape:
    """A sparse, negatively skewed seller at zero edge: one open trade per road at a time (held `hold` sessions), the
    full maximum loss (return on risk -1) with probability `loss_chance`, else the small win that makes the mean 0."""

    loss_chance: float
    hold: int = 10
    shared: float = 0.6


def seller_slots(seed: int, sessions: int, shape: SellerShape):
    draw, cut = random.Random(seed), NormalDist().inv_cdf(shape.loss_chance)
    win = shape.loss_chance / (1 - shape.loss_chance)
    shocks = [draw.gauss(0, 1) for _ in range(sessions + shape.hold)]
    next_entry = {road: draw.randrange(shape.hold) for road in ROADS}
    driver, control = {}, {}
    for i in range(sessions):
        day, common = FIRST_SESSION + timedelta(days=i), sum(shocks[i : i + shape.hold]) / shape.hold**0.5
        for road in ROADS:
            control[(day, road)] = RoadSlot(day, road, "N0@1", SlotStatus.ABSTAINED)
            if i < next_entry[road]:
                driver[(day, road)] = RoadSlot(day, road, "D@1", SlotStatus.ABSTAINED)
                continue
            latent = shape.shared**0.5 * common + (1 - shape.shared) ** 0.5 * draw.gauss(0, 1)
            driver[(day, road)] = RoadSlot(day, road, "D@1", SlotStatus.CLOSED, -1.0 if latent < cut else win)
            next_entry[road] = i + shape.hold
    return driver, control


def share_positive(make_slots, seeds: range, batch: int) -> float:
    """The share of seeded simulations whose bound against N0 is above 0: how often the descriptive bound falsely looks
    positive (v1 shows it, labelled "descriptive, not a test", and never turns it into a status)."""
    positive = 0
    for seed in seeds:
        driver, control = make_slots(seed)
        series = paired_series(driver, control, set(driver), Measure.PER_OPPORTUNITY)
        bound = paired_row("D@1", "N0@1", Measure.PER_OPPORTUNITY, series, batch, "simulation").bound
        positive += bound is not None and bound > 0
    return positive / len(seeds)


def share_watching(edge: float, sessions: int, seeds: range, batch: int, market: Market | None = None) -> float:
    """The Gaussian market's share of a positive bound (the planted-edge power and the Gaussian null)."""
    return share_positive(lambda seed: simulated_slots(seed, sessions, edge, market), seeds, batch)


def wilson_upper(share: float, n: int, z: float = 1.96) -> float:
    """The upper end of the 95% Wilson interval of a share measured on n runs (the orchestrator's gate)."""
    centre = share + z * z / (2 * n)
    spread = z * math.sqrt(share * (1 - share) / n + z * z / (4 * n * n))
    return (centre + spread) / (1 + z * z / n)


SELLER_LOSS_CHANCES = (0.05, 0.1, 0.15, 0.2)
SELLER_SEEDS = 2000


def seller_cells(holds) -> list[tuple[int, float, int, int]]:
    """The seller grid (judge 516): (hold, loss chance, sessions, batch) at each card hold and loss chance, at the
    first session count with a bound (2 batches), at twice that, at 120 and at 250 sessions."""
    cells = []
    for hold in sorted(set(holds)):
        batch = max(math.ceil(BATCH_HOLD_MULTIPLE * hold), MIN_BATCH)
        for chance in SELLER_LOSS_CHANCES:
            cells += [(hold, chance, n, batch) for n in sorted({2 * batch, 4 * batch, 120, 250})]
    return cells


def seller_cell(hold: int, chance: float, sessions: int, batch: int, seeds: int = SELLER_SEEDS) -> tuple[float, float]:
    """The seeded share of runs whose bound looks positive, and the upper end of its 95% Wilson interval."""
    share = share_positive(
        lambda seed: seller_slots(seed, sessions, SellerShape(chance, hold=hold)), range(seeds), batch
    )
    return share, wilson_upper(share, seeds)
