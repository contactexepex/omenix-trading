"""The datasets Phase 1 can promote and how each proves it is the session its path claims (docs/stories/
P1-staging-record-split.md). Participant OI, participant volume and FII statistics already prove it inside their
content check (the title's date must be the file's day). F&O and capital-market bhavcopies carry a date on every row,
which `ContentDayCheck` compares with the claimed session. index-close and security-delivery are absent on purpose:
today's readers do not read a date from them."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from fno.ingestion.storage.raw_source import (
    FiiDerivativeStatsSource,
    NseArchiveSource,
    NseDailyFoSource,
    NseEquityBhavcopySource,
    ParticipantOiSource,
    ParticipantVolumeSource,
)
from fno.ingestion.storage.source_lists import dataset_name
from fno.shared.fo_bhavcopy import read_fo_file
from fno.shared.nse_files.nse_files import read_equity_bhavcopy

ContentDays = Callable[[str, bytes], set[date]]


def fo_content_days(filename: str, data: bytes) -> set[date]:
    """The `TradDt` of every row of a daily F&O file, either format (ValueError when one is not a date)."""
    return {date.fromisoformat(row["TradDt"]) for row in read_fo_file(filename, data)}


def equity_content_days(filename: str, data: bytes) -> set[date]:
    return {bar.day for bar in read_equity_bhavcopy(data, filename)}


@dataclass(frozen=True)
class PromotableDataset:
    source: type[NseArchiveSource]
    content_days: ContentDays | None  # None: the dataset's content check already proves the date


PROMOTABLE = {
    dataset_name(d.source): d
    for d in (
        PromotableDataset(ParticipantOiSource, None),
        PromotableDataset(ParticipantVolumeSource, None),
        PromotableDataset(FiiDerivativeStatsSource, None),
        PromotableDataset(NseDailyFoSource, fo_content_days),
        PromotableDataset(NseEquityBhavcopySource, equity_content_days),
    )
}
