"""The recorded captures as the learner's input (story MS-SIM-b): every session's canonical capture of each road, read
and verified by MS-P1b's `CaptureReader` (hash against the sidecar, window, completeness). A session whose capture is
missing or fails a check is skipped and counted, never repaired, so the model rests on verified captures only."""

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import date
from itertools import groupby

from ...contracts.roads import Road
from ...contracts.snapshot import SlotSnapshot
from ...roads.capture import CaptureProblem, CaptureReader


@dataclass
class Skipped:
    """Captures left out of the model, with the closure reason each failed on."""

    reasons: list[tuple[str, date, str]] = field(default_factory=list)

    def lines(self) -> list[str]:
        """One line per road and reason naming every session left out, so no capture is only a count."""
        ordered = sorted(self.reasons, key=lambda r: (r[0], r[2], r[1]))
        return [
            f"{road} {reason}: {', '.join(day.isoformat() for _, day, _ in rows)}"
            for (road, reason), rows in ((key, list(g)) for key, g in groupby(ordered, key=lambda r: (r[0], r[2])))
        ]


def recorded_snapshots(reader: CaptureReader, roads: Iterable[Road], sessions: Iterable[date],
                       skipped: Skipped) -> Iterator[SlotSnapshot]:  # fmt: skip
    days = list(sessions)
    for road in roads:
        for session in days:
            try:
                yield reader.read(road, session).snapshot()
            except CaptureProblem as problem:
                skipped.reasons.append((road.code, session, str(problem.reason)))
