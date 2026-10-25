"""A paired series' row (story MS-INS, part d; orchestrator's rulings, 22 Oct 2026): its mean and a one-sided 95%
Student-t lower bound on non-overlapping batch means, counted back from the last session (S6's t table), both shown as
descriptive numbers, not a test. The v1 status is Exploratory below 30 sessions and Not established otherwise: never
Watching, because a skewed seller's bound looks positive falsely far more than 10% of the time (ruling D). With fewer
than 2 whole batches there is no bound and the row says so; a seller-shaped driver's row carries that false rate."""

import math
import statistics

from ....scoreboard.t_check import t_quantile
from ..contracts import MapStatus, Measure, PairedRow
from ..thresholds import MIN_BATCHES, MIN_SESSIONS, SELLER_FALSE_POSITIVE_PCT
from .series import PairedSeries

DESCRIPTIVE = "descriptive, not a test"
TOO_FEW_BATCHES = "too few independent batches: no bound before {first} sessions"
SELLER_FALSE_RATE = (
    "this method can falsely look positive up to {rate}% for this payoff shape (rarer full losses can be worse)"
)


def batch_bound(values: tuple[float, ...], batch: int) -> float | None:
    """The bound on whole batches counted back from the last session; None below `MIN_BATCHES` batches."""
    k = len(values) // batch
    if k < MIN_BATCHES:
        return None
    kept = values[len(values) - k * batch :]
    means = [sum(kept[i * batch : (i + 1) * batch]) / batch for i in range(k)]
    return statistics.fmean(means) - t_quantile(k - 1) * statistics.stdev(means) / math.sqrt(k)


def status(sessions: int) -> MapStatus:
    """v1 never assigns Watching (ruling D): it returns only when a v2 card's own null gate passes skewed shapes."""
    return MapStatus.EXPLORATORY if sessions < MIN_SESSIONS else MapStatus.NOT_ESTABLISHED


def paired_row(driver_id: str, control_id: str, measure: Measure, series: PairedSeries, batch: int,
               rules_sha256: str, seller: bool = False) -> PairedRow:  # fmt: skip
    n = len(series.days)
    bound = batch_bound(series.values, batch)
    notes = [DESCRIPTIVE]
    notes += [TOO_FEW_BATCHES.format(first=MIN_BATCHES * batch)] if n and bound is None else []
    notes += [SELLER_FALSE_RATE.format(rate=SELLER_FALSE_POSITIVE_PCT)] if seller else []
    note = "; ".join(notes)
    return PairedRow(driver_id, control_id, measure, series.days[0] if n else None, series.days[-1] if n else None, n,
                     series.road_slots, series.driver_abstentions, series.control_abstentions, series.unavailable,
                     series.after_cut, sum(series.values) / n if n else None, bound, batch, status(n),
                     rules_sha256, note)  # fmt: skip
