"""The stores-only archive for a practice run (story MS-SIM-d1, criteria 9 and 10): NSE's archived F&O files and index
closes are read from the stores, and a file that is not there stays missing. Nothing is fetched from NSE.

The library's source is MS-P1b's `StoredFilesOnly`, whose fetch returns nothing; `build_nse_*_library` is never called
here because it falls back to an NSE request (a test pins both)."""

from ....constants import PANEL_FORMAT_LEGACY, PANEL_FORMAT_UDIFF, PANEL_INDEX_CLOSE
from ....research_data.nifty_panel import DailyFiles
from ....storage.raw_library import RawFileLibrary
from ....storage.raw_source import NseDailyFoSource, NseIndexCloseSource, NseLegacyFoSource
from ....storage.wiring import daily_files
from ...roads.stored_files import StoredFilesOnly
from ...roads.wiring import build_archive_stores
from ..history.bhavcopy_chain import BhavcopyChain
from .cached_chain import CachedChain
from .index_closes import ArchivedIndexCloses


def build_stored_library(stores=None) -> RawFileLibrary:
    """The archive's stores (Drive), read only, with no source behind them."""
    return RawFileLibrary(build_archive_stores() if stores is None else stores, StoredFilesOnly())


def build_fo_files(library: RawFileLibrary) -> list[DailyFiles]:
    """The F&O files in order of precedence, current format first."""
    return [daily_files(PANEL_FORMAT_UDIFF, NseDailyFoSource, library),
            daily_files(PANEL_FORMAT_LEGACY, NseLegacyFoSource, library)]  # fmt: skip


def build_index_closes(library: RawFileLibrary) -> ArchivedIndexCloses:
    return ArchivedIndexCloses(daily_files(PANEL_INDEX_CLOSE, NseIndexCloseSource, library))


def build_history_chain(library: RawFileLibrary) -> CachedChain:
    """Every archived day as a `DayChain`, legacy days taking their index close from the archived index-close file."""
    return CachedChain(BhavcopyChain(build_fo_files(library), index_close=build_index_closes(library)))
