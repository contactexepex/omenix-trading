"""One driver against one control as a series of sessions (story MS-INS, part d; 327 correction 2): on each common
road-day both decided, the difference of their values; one point per session, the mean over its roads, so five roads
on one day are one point. The series stops at the first session with a pair still open (S3's cut); closed pairs after
it are counted in `after_cut`, never part of the series. `unavailable` counts every common road-day left out (either
side unavailable, or missing from its map), before and after the cut. Under executed-only an open ticket does not
cut: its value there is already 0."""

from collections import defaultdict
from collections.abc import Collection, Mapping
from dataclasses import dataclass
from datetime import date

from ...constants import RoadCode
from ..contracts import Measure
from .values import RoadSlot, SlotStatus

RoadDay = tuple[date, RoadCode]


@dataclass(frozen=True)
class PairedSeries:
    days: tuple[date, ...]
    values: tuple[float, ...]  # per session: the mean over its roads of driver minus control
    road_slots: int
    driver_abstentions: int
    control_abstentions: int
    unavailable: int
    after_cut: int


def _missing(road_day: RoadDay) -> RoadSlot:
    return RoadSlot(road_day[0], road_day[1], "", SlotStatus.UNAVAILABLE)


def _open(slot: RoadSlot, measure: Measure) -> bool:
    return slot.status == SlotStatus.OPEN and not (measure == Measure.EXECUTED and slot.is_ticket)


def value(slot: RoadSlot, measure: Measure) -> tuple[float, bool]:
    """The slot's value and whether it counts as an abstention under the measure (a ticket is one, executed-only)."""
    if slot.status == SlotStatus.ABSTAINED or (measure == Measure.EXECUTED and slot.is_ticket):
        return 0.0, True  # an open ticket under executed-only lands here too
    return slot.return_on_risk, False


def paired_series(driver: Mapping[RoadDay, RoadSlot], control: Mapping[RoadDay, RoadSlot], common: Collection[RoadDay],
                  measure: Measure) -> PairedSeries:  # fmt: skip
    by_session: dict[date, list[tuple[RoadSlot, RoadSlot]]] = defaultdict(list)
    for road_day in sorted(common):
        by_session[road_day[0]].append(
            (driver.get(road_day, _missing(road_day)), control.get(road_day, _missing(road_day)))
        )
    days, values, counts, cut, after = [], [], [0, 0, 0, 0], False, 0
    for session in sorted(by_session):
        pairs = [p for p in by_session[session] if SlotStatus.UNAVAILABLE not in (p[0].status, p[1].status)]
        counts[3] += len(by_session[session]) - len(pairs)
        cut = cut or any(_open(d, measure) or _open(c, measure) for d, c in pairs)
        if cut:
            after += sum(not (_open(d, measure) or _open(c, measure)) for d, c in pairs)
            continue
        if not pairs:
            continue
        diffs = []
        for d, c in pairs:
            (dv, d_abstained), (cv, c_abstained) = value(d, measure), value(c, measure)
            diffs.append(dv - cv)
            counts[0], counts[1], counts[2] = counts[0] + 1, counts[1] + d_abstained, counts[2] + c_abstained
        days.append(session)
        values.append(sum(diffs) / len(diffs))
    return PairedSeries(tuple(days), tuple(values), counts[0], counts[1], counts[2], counts[3], after)
