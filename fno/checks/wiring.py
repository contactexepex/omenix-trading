"""Composition root of the data checks (story C3): the checks in the order they report, the quote store the snapshot
is read from, the shock flag source, the NSE file stores and the alert sender. Also of the hard-validity checks (story
C4): the evidence store, the charge table and owner limits from config.yaml, each book's mode, the failure log. Swapping
any changes this file only."""

from __future__ import annotations

from pathlib import Path

from .data_checks import DataChecks
from .gate import DataGate
from .leg_checks import LegQuotesValid
from .market_checks import PreviousSessionFile, SpotNearPreviousClose
from .schedule import ExecutionSchedule, PackSnapshotSchedule
from .shock import NoShockFlags
from .snapshot_checks import SnapshotInWindow, SnapshotMatchesRecord, SnapshotReadable
from .validity import Sources, ValidityChecker
from .validity_account import LedgerAccounts
from .validity_adapter import BookTradeValidator, CaptureSource
from .validity_evidence import EvidenceReader
from .validity_limits import LimitChecks
from .validity_listing import NseListing
from .validity_margin import MarginFile
from .validity_modes import PlaybookMode, ValidityMode
from .validity_settings import limits_from_config
from .validity_shapes import BOUGHT, CALL, PUT, SOLD, BodyWithWings, OneBoughtOption, Shape, Vertical


def build_data_checks(stores, calendar, shocks=None) -> DataChecks:
    from ..storage.raw_source import NseDailyFoSource

    return DataChecks(
        (
            SnapshotReadable(),
            SnapshotInWindow(),
            SnapshotMatchesRecord(),
            SpotNearPreviousClose(calendar, shocks or NoShockFlags()),
            LegQuotesValid(),
            PreviousSessionFile(stores, NseDailyFoSource, calendar),
        )
    )


def build_data_gate(quote_folder: Path | None = None, schedule: ExecutionSchedule | None = None) -> DataGate:
    """The gate the desk runs before each decision; E3 passes its own execution schedule."""
    from ..composition import build_alert_sender, build_session_calendar
    from ..desk.wiring import build_execution_snapshots
    from ..storage.wiring import build_raw_stores

    checks = build_data_checks(build_raw_stores(), build_session_calendar())
    snapshots = build_execution_snapshots(quote_folder)
    return DataGate(checks, snapshots, schedule or PackSnapshotSchedule(), build_alert_sender())


def validity_shapes() -> dict[str, Shape]:
    """C4's own shape rule for every structure code D1 accepts (B2's four-leg codes and STR1's six)."""
    from .. import constants as c

    return {
        c.STRUCTURE_SHORT_IRON_FLY: BodyWithWings(SOLD, one_body_strike=True),
        c.STRUCTURE_SHORT_CONDOR: BodyWithWings(SOLD, one_body_strike=False),
        c.STRUCTURE_LONG_IRON_FLY: BodyWithWings(BOUGHT, one_body_strike=True),
        c.STRUCTURE_LONG_CALL: OneBoughtOption(CALL),
        c.STRUCTURE_LONG_PUT: OneBoughtOption(PUT),
        c.STRUCTURE_CALL_DEBIT_SPREAD: Vertical(CALL, BOUGHT),
        c.STRUCTURE_CALL_CREDIT_SPREAD: Vertical(CALL, SOLD),
        c.STRUCTURE_PUT_DEBIT_SPREAD: Vertical(PUT, BOUGHT),
        c.STRUCTURE_PUT_CREDIT_SPREAD: Vertical(PUT, SOLD),
    }


def validity_modes(root: Path | None = None) -> dict[str, ValidityMode]:
    """Book 1 checks against the playbook; Book 2 against the playbook and its trade envelope (D4); Book 3 against its
    constitution and strategy registry (D5); the files, the D6 registry and git history under `root`."""
    from ..book3.constitution import ConstitutionFiles
    from ..book3.wiring import build_strategy_registry
    from ..books.registered_components import RegisteredComponents
    from ..books.version_registry import VersionRegistry
    from ..books.versions import VERSIONS_FILE
    from ..config import ROOT
    from ..constants import BOOK1_RULES, BOOK2_HYBRID, BOOK3_AI
    from ..playbook.envelope_files import EnvelopeFiles
    from ..research_engine.ledger import Git
    from .validity_constitution import ConstitutionMode
    from .validity_envelope import EnvelopeMode

    base = Path(root or ROOT)
    registered = RegisteredComponents(VersionRegistry(base / VERSIONS_FILE))
    return {
        BOOK1_RULES: PlaybookMode(validity_shapes()),
        BOOK2_HYBRID: EnvelopeMode(validity_shapes(), EnvelopeFiles(base).all, registered),
        BOOK3_AI: ConstitutionMode(
            validity_shapes(),
            ConstitutionFiles(base).by_sha256,
            registered,
            build_strategy_registry(base),
            Git(base).head,
        ),  # fmt: skip
    }


def build_validity_checker(cfg: dict, root: Path, quotes, nse_library, accounts=None, margins=None) -> ValidityChecker:
    """C4's checker: the A4 quote store, NSE's F&O files (A2's library), the books' ledgers and A14's margins file;
    charges and the books' risk profile read straight from config.yaml, never through C2 or B2."""
    from ..constants import RISK_PROFILE_BOOKS
    from ..quotes.recorder import DATASET
    from ..storage.wiring import build_session_calendar

    limits = limits_from_config(cfg, root, RISK_PROFILE_BOOKS, build_session_calendar().session_kind)
    sources = Sources(EvidenceReader(quotes, DATASET), NseListing(nse_library), accounts or LedgerAccounts(root))
    checks = LimitChecks(limits, cfg["charges"], margins or MarginFile(limits.margins.file))
    return ValidityChecker(sources, checks, validity_modes(root))


def build_trade_validator(
    cfg: dict, book: str, root: Path, captures: CaptureSource | None = None, log: bool = True,
    quote_folder: Path | None = None,
) -> BookTradeValidator:  # fmt: skip
    """The validator D3's decision run calls for `book`; a replay passes `log=False` so it writes nothing."""
    from ..composition import DESK_DECISION_TIME
    from ..desk.pack_store import PackStore
    from ..storage.wiring import build_nse_fo_library, build_quote_store
    from .validity_capture import PackCaptures
    from .validity_failures import ValidityFailureLog

    checker = build_validity_checker(cfg, root, build_quote_store(quote_folder), build_nse_fo_library())
    captures = captures or PackCaptures(PackStore(root), PackSnapshotSchedule())
    return BookTradeValidator(book, checker, captures, DESK_DECISION_TIME, ValidityFailureLog(root) if log else None)
