"""The content check of each raw dataset (stories A1, A8, P6, A20a, A23): a function of a file's name and bytes that
raises BadFile (a ValueError) when the file is damaged or not in its publisher's layout. The coverage check, the
librarian and the snapshot takers use the same checks."""

from __future__ import annotations

from ..constants import INDEX_INDIA_VIX, INDEX_NIFTY_50
from ..fo_bhavcopy import BadFile, read_fo_file, read_index_closes
from ..market_read_models.corporate_actions import read_corporate_actions
from ..market_read_models.flows_files import read_fii_dii, read_nsdl_equity
from ..market_read_models.nse_files import read_delivery, read_equity_bhavcopy, read_equity_list, read_nifty500_list
from ..market_read_models.symbol_changes import read_symbol_changes
from ..nse_margins.span_file import read_span_file
from ..research_data.fii_derivative_stats import read_fii_derivative_stats
from ..research_data.fo_masters import ban_list_trade_date, read_ban_list, read_lot_sizes
from ..research_data.participant_oi import read_participant_oi
from ..research_data.participant_volume import read_participant_volume
from .raw_source import (
    FiiDerivativeStatsSource,
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

REQUIRED_INDICES = (INDEX_NIFTY_50, INDEX_INDIA_VIX)


def validate_index_close(filename: str, data: bytes) -> None:
    missing = [name for name in REQUIRED_INDICES if name not in read_index_closes(data, filename)]
    if missing:
        raise BadFile(f"{filename}: no closing value for {missing}")


def validate_participant_oi(filename: str, data: bytes) -> None:
    read_participant_oi(data, filename, ParticipantOiSource.day_for(filename))


def validate_participant_volume(filename: str, data: bytes) -> None:
    """Participant OI's layout and identities, rows without a participant name ignored (A23 back-fill)."""
    read_participant_volume(data, filename, ParticipantVolumeSource.day_for(filename))


def validate_fii_derivative_stats(filename: str, data: bytes) -> None:
    read_fii_derivative_stats(data, filename, FiiDerivativeStatsSource.day_for(filename))


VALIDATORS = {
    NseLegacyFoSource: read_fo_file,
    NseDailyFoSource: read_fo_file,
    NseIndexCloseSource: validate_index_close,
    ParticipantOiSource: validate_participant_oi,
    ParticipantVolumeSource: validate_participant_volume,
    FiiDerivativeStatsSource: validate_fii_derivative_stats,
    NseEquityBhavcopySource: lambda filename, data: read_equity_bhavcopy(data, filename),
    NseDeliverySource: lambda filename, data: read_delivery(data, filename),
    EquityListSource: lambda filename, data: read_equity_list(data, filename),
    Nifty500ListSource: lambda filename, data: read_nifty500_list(data, filename),
    SymbolChangeSource: lambda filename, data: read_symbol_changes(data, filename),
    FiiDiiCashSource: lambda filename, data: read_fii_dii(data, filename),
    NsdlFpiDailySource: lambda filename, data: read_nsdl_equity(data, filename),
    FiiDiiCashBySessionSource: lambda filename, data: read_fii_dii(data, filename),
    NsdlFpiDailyBySessionSource: lambda filename, data: read_nsdl_equity(data, filename),
    CorporateActionsSource: lambda filename, data: read_corporate_actions(data, filename),
    CorporateActionsBySymbolSource: lambda filename, data: read_corporate_actions(data, filename),
    # a valid SPAN file of any method A14c reads (2020's minimum included); A14's daily job still refuses that method
    NseSpanBodSource: lambda filename, data: read_span_file(data, filename, allow_short_option_minimum=True),
    FoBanListSource: lambda filename, data: read_ban_list(data, filename),
    FoLotSizeSource: lambda filename, data: read_lot_sizes(data, filename),
}

# The session a copy covers, read from the copy itself: where the by-session series files it (judge 66, P8; A20a)
COVERED_SESSION = {
    FoBanListSource: ban_list_trade_date,
    FiiDiiCashBySessionSource: lambda filename, data: read_fii_dii(data, filename).day,
    NsdlFpiDailyBySessionSource: lambda filename, data: read_nsdl_equity(data, filename)[0],
}
