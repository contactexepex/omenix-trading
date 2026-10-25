"""Each road's earlier recorded 15:00 spots (story MS-P1j; the drivers' history, story 3.2): read from the repository's
committed sidecars of the road's canonical captures, strictly before the session. No Drive and no new read: a sidecar
is the record the 3 pm recorder committed, and its `spot` is Groww's chain spot at the capture. A session without a
canonical capture, or whose capture was incomplete, out of window or without a spot, adds no point."""

import json
from datetime import date
from pathlib import Path

from ...quotes.recorder import NONE_MARKER, QuoteSnapshotRecorder
from ..contracts.decisions import SpotPoint
from ..contracts.roads import Road

MARKER = "{stem}_{day:%Y%m%d}.canonical"


class RecordedSpotHistory:
    def __init__(self, folder: Path):
        self.folder = Path(folder)

    def spots(self, road: Road, session: date) -> tuple[SpotPoint, ...]:
        points = []
        for marker in sorted(self.folder.glob(f"{road.dataset}/*/*/{road.stem}_*.canonical")):
            day = _day(marker.name, road.stem)
            if day is None or day >= session:
                continue
            spot = self._spot(road, day, marker.read_text().strip())
            if spot is not None:
                points.append(SpotPoint(day, spot))
        return tuple(points)

    def _spot(self, road: Road, day: date, snapshot_id: str) -> float | None:
        if not snapshot_id or snapshot_id == NONE_MARKER:
            return None
        sidecar = self.folder / QuoteSnapshotRecorder.path(day, f"{snapshot_id}.meta.json", road.dataset)
        try:
            meta = json.loads(sidecar.read_text())
        except (OSError, ValueError):
            return None
        spot = meta.get("spot")
        usable = meta.get("complete") is True and meta.get("in_window") is True
        return float(spot) if usable and isinstance(spot, (int, float)) and spot > 0 else None


def _day(name: str, stem: str) -> date | None:
    digits = name.removeprefix(f"{stem}_").removesuffix(".canonical")
    try:
        return date(int(digits[:4]), int(digits[4:6]), int(digits[6:8])) if len(digits) == 8 else None
    except ValueError:
        return None
