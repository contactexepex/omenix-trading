"""Composition root of the role-value evaluation (story F9a): the paired rows and role sets, the real runs and the
shadow runs, E2's common packs, scoreboard A's standard unit (S3), E3's run-log snapshots, F8's allocation and usage
ledger, S1's review dates on the NSE calendar, C4's failure log and the protocol's label. Swapping any source changes
this file only."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from functools import cache
from pathlib import Path

from ..budget.allocation import Allocation
from ..checks.validity_failures import ValidityFailureLog
from ..config import ROOT
from ..constants import NIFTY_SYMBOL
from ..desk.settlement import SettlementPrices
from ..desk.snapshot import ExecutionSnapshotSource
from ..evaluation.review_dates import review_dates
from ..models import today_local
from ..risk.open_risk import HeldMaxLoss
from ..scoreboard.committed_runs import CommittedRuns
from ..scoreboard.matched_days import CommonPacks
from ..scoreboard.ports import ProtocolStatus
from ..scoreboard.sources import DaySnapshots
from ..scoreboard.standard_unit import SessionsBetween, StandardUnit
from .controls import control_counts
from .records import CollectedRunRecords, ShadowRecordFiles
from .report import RoleValueInputs, RoleValueReport
from .role_set_file import RoleUnitsFile
from .rows import PairedRowFile


def role_value_report_from(
    root: Path, cfg: dict, sessions: SessionsBetween, snapshots: ExecutionSnapshotSource,
    settlements: SettlementPrices, protocol: ProtocolStatus, allocation_of: Callable[[str], Allocation],
    usage_of: Callable[[str], Sequence[Mapping]],
) -> RoleValueReport:  # fmt: skip
    runs = CommittedRuns(root)
    ids = runs.snapshot_ids()
    unit = StandardUnit(DaySnapshots(snapshots, ids), sessions, settlements, HeldMaxLoss(cfg["charges"]),
                        cfg["charges"], cfg["lot_sizes"][NIFTY_SYMBOL])  # fmt: skip
    failures = ValidityFailureLog(root)
    return RoleValueReport(RoleValueInputs(
        source=PairedRowFile(root), role_set_of=RoleUnitsFile(root).role_set, real=CollectedRunRecords(runs),
        shadow=ShadowRecordFiles(root), packs=CommonPacks(root).day, unit=unit, run_log_snapshots=ids,
        allocation_of=cache(allocation_of), usage_of=cache(usage_of),  # each month read once per report
        review_days=lambda start, through: review_dates(start, sessions, through),
        controls=lambda book, first, last: control_counts(failures, book, first, last), protocol=protocol.label,
    ))  # fmt: skip


def build_role_value_report(cfg: dict, root: Path = ROOT) -> RoleValueReport:
    from ..budget.usage_ledger import UsageLedger
    from ..budget.wiring import build_month_meter
    from ..composition import build_session_calendar
    from ..desk.settlement import NseFinalSettlement
    from ..desk.wiring import build_execution_snapshots
    from ..scoreboard.protocol_status import protocol_status
    from ..storage.wiring import build_nse_fo_library

    ledger = UsageLedger(root)
    return role_value_report_from(
        root, cfg, build_session_calendar().sessions, build_execution_snapshots(),
        NseFinalSettlement(build_nse_fo_library()), protocol_status(root),
        lambda month: build_month_meter(month, today_local(), root, cfg).allocation,
        lambda month: [row for row in ledger.rows() if row["date"].startswith(month)],
    )  # fmt: skip
