"""Composition root of scoreboards B (story S2) and A (story S3): the three books' records, E3's run logs and D3's
stores, D6's versions, the session calendar, the recorded execution snapshots for marks and one-lot fills, C1's
charges and operating costs, E7's final settlement, the AI cost until F8, F7's matched shadow decisions (none until F7)
and the protocol's status (S1). Swapping any source changes this file only."""

from __future__ import annotations

from pathlib import Path

from ..books.account import PaperAccount
from ..books.versions import Versions
from ..config import ROOT
from ..constants import BOOKS, NIFTY_SYMBOL
from ..desk.records import DeskRecords
from ..desk.settlement import SettlementPrices
from ..desk.snapshot import ExecutionSnapshotSource
from ..research_data.calendar import SessionCalendar
from ..risk.open_risk import HeldMaxLoss
from .book_board import BookBoard
from .committed_runs import CommittedRuns
from .daily_values import DayMarks
from .do_nothing import DoNothing, Terms
from .entry_decisions import EntryDecisions
from .matched_board import MatchedBoard
from .matched_days import CommonPacks, MatchedDays
from .ports import ProtocolStatus
from .random_control import RandomControl
from .sources import (
    AiCostBeforeF8,
    ArchivedIndexLevels,
    DaySnapshots,
    FileOperatingCosts,
    NoMatchedShadowYet,
    RecordedOwnerOverride,
    SnapshotMarks,
    input_hashes,
)  # fmt: skip
from .standard_unit import StandardUnit
from .whole_system import WholeSystemBoard

INDEX_UNREACHABLE = "not computable: the archived index files cannot be read (Drive settings missing)"


def board_from(
    root: Path, charges: dict, calendar: SessionCalendar, versions: Versions, marks: DayMarks,
    protocol: ProtocolStatus, brake_rs: float | None = None, do_nothing: DoNothing | None = None,
    luck: RandomControl | None = None,
) -> WholeSystemBoard:  # fmt: skip
    runs, board = CommittedRuns(root), BookBoard(calendar.sessions, AiCostBeforeF8(), brake_rs, do_nothing, luck)
    return WholeSystemBoard(
        BOOKS, lambda book: DeskRecords(PaperAccount(root, book)),
        lambda: EntryDecisions(runs.runs(), runs.records, versions, RecordedOwnerOverride()), calendar.sessions, marks,
        FileOperatingCosts(root), board, charges, protocol,
        lambda: input_hashes(root, BOOKS, runs.runs()), runs.uncollected, runs.missed_runs,
    )  # fmt: skip


def build_whole_system_board(cfg: dict, root: Path = ROOT) -> WholeSystemBoard:
    from ..composition import build_session_calendar, build_versions
    from ..desk.wiring import build_execution_snapshots
    from .protocol_status import protocol_status

    snapshots, ids = build_execution_snapshots(), CommittedRuns(root).snapshot_ids()
    books = cfg["risk"]["profiles"]["books"]  # the books' brake, caps and bucket sides (story S6)
    luck = RandomControl(DaySnapshots(snapshots, ids), HeldMaxLoss(cfg["charges"]), cfg["charges"],
                         books["max_loss_per_trade_rs"], books["bucket_cap_rs"], books["bucket_sides"])  # fmt: skip
    return board_from(
        root, cfg["charges"], build_session_calendar(), build_versions(root), SnapshotMarks(snapshots, ids),
        protocol_status(root), books["drawdown_brake_rs"], do_nothing(cfg), luck,
    )  # fmt: skip


def do_nothing(cfg: dict) -> DoNothing:
    """Story S6's comparison: the archived index-close files and the books' account capital."""
    raw = drive_raw_or_none()
    terms = Terms(cfg["risk"]["profiles"]["books"]["paper_account_rs"])
    return DoNothing(ArchivedIndexLevels(raw), terms, "" if raw else INDEX_UNREACHABLE)


def drive_raw_or_none():
    """Drive's raw area, or None without its settings: the do-nothing comparison then names that cause."""
    from ..storage.wiring import build_drive_reader

    try:
        return build_drive_reader()
    except RuntimeError:
        return None


def matched_board_from(
    root: Path, cfg: dict, calendar: SessionCalendar, versions: Versions, snapshots: ExecutionSnapshotSource,
    settlements: SettlementPrices, protocol: ProtocolStatus, against: DoNothing | None = None,
) -> MatchedBoard:  # fmt: skip
    runs = CommittedRuns(root)
    days = DaySnapshots(snapshots, runs.snapshot_ids())
    unit = StandardUnit(days, calendar.sessions, settlements, HeldMaxLoss(cfg["charges"]), cfg["charges"],
                        cfg["lot_sizes"][NIFTY_SYMBOL])  # fmt: skip
    logged = [day for day, _ in runs.logs()]
    return MatchedBoard(
        BOOKS, lambda decisions: MatchedDays(runs.runs(), runs.records, decisions, CommonPacks(root).day,
                                             set(runs.snapshot_ids()), NoMatchedShadowYet()),
        lambda: EntryDecisions(runs.runs(), runs.records, versions, RecordedOwnerOverride()), CommonPacks(root).day,
        calendar.sessions, unit, lambda: min(logged) if logged else None, protocol.label, against,
    )  # fmt: skip


def build_matched_board(cfg: dict, root: Path = ROOT) -> MatchedBoard:
    from ..composition import build_session_calendar, build_versions
    from ..desk.settlement import NseFinalSettlement
    from ..desk.wiring import build_execution_snapshots
    from ..storage.wiring import build_nse_fo_library
    from .protocol_status import protocol_status

    return matched_board_from(
        root, cfg, build_session_calendar(), build_versions(root), build_execution_snapshots(),
        NseFinalSettlement(build_nse_fo_library()), protocol_status(root), do_nothing(cfg),
    )  # fmt: skip
