"""Every raw dataset's source, grouped by how it is archived (apart from `wiring.py`, which is at the size limit)."""

from __future__ import annotations

from .raw_source import (
    FiiDerivativeStatsSource,
    NseArchiveSource,
    NseDailyFoSource,
    NseDeliverySource,
    NseEquityBhavcopySource,
    NseIndexCloseSource,
    NseLegacyFoSource,
    NseSpanBodSource,
    ParticipantOiSource,
    ParticipantVolumeSource,
)
from .snapshot_source import (
    CorporateActionsBySymbolSource,
    CorporateActionsSource,
    EquityListSource,
    FiiDiiCashBySessionSource,
    FiiDiiCashSource,
    FoBanListSource,
    FoLotSizeSource,
    Nifty500ListSource,
    NsdlFpiDailyBySessionSource,
    NsdlFpiDailySource,
    SymbolChangeSource,
)

DATED_SOURCES = (
    NseLegacyFoSource,
    NseDailyFoSource,
    NseIndexCloseSource,
    ParticipantOiSource,
    NseEquityBhavcopySource,
    NseDeliverySource,
    NseSpanBodSource,
    ParticipantVolumeSource,
    FiiDerivativeStatsSource,
)  # one file per session: the coverage check's datasets
SNAPSHOT_SOURCES = (
    EquityListSource,
    Nifty500ListSource,
    SymbolChangeSource,
    CorporateActionsSource,
    CorporateActionsBySymbolSource,
    FiiDiiCashBySessionSource,
    NsdlFpiDailyBySessionSource,
    FoBanListSource,
    FoLotSizeSource,
)  # reference lists, one copy per day fetched (P6, A20a); one copy per session covered (P8 flows, A20a ban list)
RUN_DATED_FLOWS = (FiiDiiCashSource, NsdlFpiDailySource)  # P8's first copies, filed by run day: kept, never taken again
RAW_SOURCES = DATED_SOURCES + SNAPSHOT_SOURCES + RUN_DATED_FLOWS  # every dataset with a manifest


def dataset_name(source: type[NseArchiveSource]) -> str:
    return source.dataset.rsplit("/", 1)[-1]


# Datasets the librarian may upload: each new one needs its own story (A9: participant OI; A10: index closes; P6: the
# equity, delivery and current-format F&O files the market read models need each day, and the reference lists; A14:
# the beginning-of-day SPAN files; A23: participant volume and FII derivatives statistics, the flow history.
LIBRARIAN_DATASETS = {
    dataset_name(s): s
    for s in (
        ParticipantOiSource,
        NseIndexCloseSource,
        NseEquityBhavcopySource,
        NseDeliverySource,
        NseDailyFoSource,
        NseSpanBodSource,
        ParticipantVolumeSource,
        FiiDerivativeStatsSource,
    )
}
SNAPSHOT_DATASETS = {dataset_name(s): s for s in SNAPSHOT_SOURCES}
FINGERPRINT_SOURCES = {dataset_name(s): s for s in DATED_SOURCES}
