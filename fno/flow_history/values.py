"""One reader per flow dataset (story A23), behind one port: a session's file as `(series, measure, value)` triples,
the derived table's long form (a new index row in a later file is one more series, never a new column). Each reader
raises the dataset's BadFile for a damaged file, so the table never takes a file partly."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict
from datetime import date

from ..constants import PARTICIPANTS
from ..research_data.fii_derivative_stats import read_fii_derivative_stats
from ..research_data.participant_volume import read_participant_volume
from ..storage.raw_source import FiiDerivativeStatsSource, NseArchiveSource, ParticipantVolumeSource

Triple = tuple[str, str, str]
BOUGHT, SOLD = "bought", "sold"  # participant volume: the file's "Long" and "Short" columns are contracts traded
TOTAL = "total"


class FlowValues(ABC):
    source: type[NseArchiveSource]

    @abstractmethod
    def values(self, data: bytes, day: date) -> list[Triple]:
        """The session's values; BadFile when the file is damaged or for another day."""


class ParticipantVolumeValues(FlowValues):
    source = ParticipantVolumeSource

    def values(self, data: bytes, day: date) -> list[Triple]:
        volume = read_participant_volume(data, self.source.filename_for(day), day)
        triples = []
        for participant in PARTICIPANTS:
            sides = {**volume.positions[participant], TOTAL: volume.totals[participant]}
            for group, side in sides.items():
                series = f"{participant}:{group}"
                triples += [(series, BOUGHT, str(side.long)), (series, SOLD, str(side.short))]
        return triples


class FiiDerivativeStatsValues(FlowValues):
    source = FiiDerivativeStatsSource

    def values(self, data: bytes, day: date) -> list[Triple]:
        stats = read_fii_derivative_stats(data, self.source.filename_for(day), day)
        rows = {**stats.groups, **stats.indices}
        return [(label, measure, str(value)) for label, flow in rows.items() for measure, value in asdict(flow).items()]
