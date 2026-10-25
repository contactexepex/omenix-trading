"""The paper desk's daily timetable (story E3, design 13.5 steps 4-5): when the common pack is built, when decisions
are collected (the hard deadline), when the execution snapshot is taken, and by when fills and exits finish. The times
come from `config.yaml` `desk.timetable`, PROPOSED until S1 freezes them from measured run times."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time

from ..models import IST

ORDER = ("pack", "pack_wait_until", "decision_deadline", "execution_snapshot", "fills_by")


class TimetableError(ValueError):
    """The timetable in config.yaml is missing a time or its times are out of order."""


@dataclass(frozen=True)
class Timetable:
    pack: time
    pack_wait_until: time
    decision_deadline: time
    execution_snapshot: time
    fills_by: time
    lock_lease_seconds: float  # one book's account write inside the fills window (E1's default is 600 s)

    def at(self, day: date, moment: time) -> datetime:
        return datetime.combine(day, moment, IST)


def timetable_from_config(cfg: dict) -> Timetable:
    """The timetable in `desk.timetable`; refused when a time is missing or the order is wrong."""
    raw = cfg.get("desk", {}).get("timetable", {})
    try:
        times = [time.fromisoformat(str(raw[name])) for name in ORDER]
        lease = float(raw["lock_lease_seconds"])
    except (KeyError, ValueError) as missing:
        raise TimetableError(f"config.yaml desk.timetable: {missing}") from missing
    if times != sorted(times) or len(set(times)) != len(times):
        raise TimetableError(f"config.yaml desk.timetable: {', '.join(ORDER)} must be strictly in this order")
    window = (datetime.combine(date.min, times[-1]) - datetime.combine(date.min, times[-2])).total_seconds()
    if not 0 < lease < window:
        raise TimetableError(f"desk.timetable.lock_lease_seconds must be above 0 and below the fills window ({window})")
    return Timetable(*times, lease)
