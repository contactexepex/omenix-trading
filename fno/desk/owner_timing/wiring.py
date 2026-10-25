"""Composition root of the owner-timing fills (story E8): the only place that picks A16's copies and the A4 stand-in,
the private availability file and its committed seals, the card's delivery record, E8's own records, the exit alert's
poster, C2's rules for the fill-day check and the owner's entry rule (`ApprovedLimit`, DESK_DECISIONS row "E8 entry
rule: price cap only"). Every Drive read of the step goes through one read-only store capped at 60 seconds a call
within the step's 10 minutes; writes go to write-once paths or E2c's journal and are never abandoned."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from pathlib import Path

from ...alerts.sender import AlertSender
from ...config import ROOT
from ...constants import BOOK1_RULES, PAPER_AREA, VERDICT_REACTION_MINUTES, VIEW_VERDICT
from ...storage.raw_store import AreaStore, RawFileStore
from ..daily_ports import DayStep
from ..entries import EntryFiller
from ..exit_timing import ExitTiming
from .availability import AvailabilitySealer, SealedDriveAvailability
from .first_use import OpenedOnFirstUse
from .live_switch import LiveFromEntries, LiveFromExits, LiveFromStep
from .order_record import KeptOrders
from .seal_log import GitSealLog
from .step import OwnerTimingStep
from .timed_reads import StepDeadline, TimedIndexStore, TimedStore
from .timing_log import StoreTimingLog

SEALS_FILE = "research/desk/availability_seals.csv"  # committed: hashes and line counts only, never a date or the salt
AVAILABILITY_FILE = "owner/availability.csv"  # in Drive's private paper area, edited by the owner only
TIMING_AREA = "owner_timing"  # E8's own records, beside the paper accounts in Drive
DRIVE_MISSING = "the owner-timing fills need Drive's owner settings ({settings})"


def _paper_drive() -> RawFileStore:
    from ...storage.wiring import OWNER_UPLOAD_SETTINGS, build_owner_drive

    drive = build_owner_drive()
    if drive is None:
        raise RuntimeError(DRIVE_MISSING.format(settings=", ".join(OWNER_UPLOAD_SETTINGS)))
    return AreaStore(drive, PAPER_AREA)


def _timing_store() -> RawFileStore:
    return OpenedOnFirstUse("owner-timing records", lambda: AreaStore(_paper_drive(), TIMING_AREA))


def build_owner_timing_desks(cfg: dict, live_from: date | None, base: EntryFiller) -> tuple[EntryFiller, ExitTiming]:
    """What the daily run's fills and exits steps use: from E8's live date, the hand-over of entries and the exit
    alert in place of E4's fill and close at the execution snapshot."""
    from ...cards.wiring import build_card_poster
    from .exit_alerts import AlertThenWait
    from .pending_entries import PendingEntries

    store = _timing_store()
    poster = build_card_poster()  # T1's poster: Slack's own server time is the exit's order time
    entries = LiveFromEntries(live_from, base, PendingEntries(VERDICT_REACTION_MINUTES, KeptOrders(store, store)))
    return entries, LiveFromExits(live_from, AlertThenWait(poster, StoreTimingLog(store, store)))


def build_owner_timing_step(cfg: dict, alerts: AlertSender, exit_timing: ExitTiming, live_from: date | None,
                            books: Sequence[str] = (BOOK1_RULES,), root: Path = ROOT) -> DayStep:  # fmt: skip
    """Rule 11's step for the verdict accounts. Its account writes are E2c's (lock, pull, push); their public totals
    are committed by the daily run with the step's entry."""
    from ...books.account import PaperAccount
    from ...cards.committed import GitHeadRecords
    from ...cards.deliveries import RepoDeliveryFiles
    from ...models import now_ist
    from ..records import DeskRecords
    from ..timetable import timetable_from_config
    from ..wiring import build_private_files, open_desk_journal
    from .account_writes import StepAccountWrites
    from .order_times import DeliveredCards

    deadline, timing = StepDeadline(), _timing_store()
    paper, log = (
        TimedStore(OpenedOnFirstUse("paper area", _paper_drive), deadline),
        StoreTimingLog(TimedStore(timing, deadline), timing),
    )
    seals = GitSealLog(root, SEALS_FILE)
    files = build_private_files(root, wrap=lambda store: TimedIndexStore(store, deadline))
    lease = timetable_from_config(cfg).lock_lease_seconds
    writes = StepAccountWrites(lambda book: open_desk_journal(book, root, lease, files), root)
    availability = SealedDriveAvailability(paper, AVAILABILITY_FILE, seals)
    entries, exits = _fills(cfg, root, availability, deadline, log, alerts, exit_timing)
    return LiveFromStep(live_from, OwnerTimingStep(
        books, AvailabilitySealer(paper, AVAILABILITY_FILE, seals), root / SEALS_FILE, writes,
        lambda book: DeskRecords(PaperAccount(root, book)),
        KeptOrders(TimedStore(timing, deadline), timing),
        DeliveredCards(RepoDeliveryFiles(root, GitHeadRecords(root))), log, entries, exits, deadline, now_ist,
    ), alerts)  # fmt: skip


def _fills(cfg: dict, root: Path, availability, deadline: StepDeadline, log: StoreTimingLog, alerts: AlertSender,
           exit_timing: ExitTiming):  # fmt: skip
    from ...books.book1_records import recorded_terms
    from ...constants import RISK_PROFILE_BOOKS
    from ...intraday.ledger import SlotLedger
    from ...intraday.wiring import INTRADAY_FOLDER
    from ...models import now_ist
    from ...research_engine.implied_vol import Black76
    from ...risk.book_view import load_risk_book
    from ...risk.profile_settings import profile_settings
    from ...risk.wiring import build_risk_manager
    from ...storage.wiring import RAW_AREA, build_owner_drive, build_quote_store, build_session_calendar
    from ..snapshot import RecordedExecutionSnapshots
    from ..wiring import build_exit_desk
    from .clock import OwnerTimingClock
    from .due_fill import DueFill
    from .entry_fills import OwnerTimingEntries
    from .entry_range import ApprovedLimit
    from .exit_fills import OwnerTimingExits
    from .fill_risk import FillDayRisk
    from .mark_snapshots import CaptureStandIn, FirstAvailable, IntradayMarkSnapshots

    raw = TimedStore(OpenedOnFirstUse("raw area", lambda: AreaStore(build_owner_drive(), RAW_AREA)), deadline)
    quotes = TimedStore(build_quote_store(), deadline)
    snapshots = FirstAvailable(
        IntradayMarkSnapshots(raw, SlotLedger(INTRADAY_FOLDER)),
        CaptureStandIn(RecordedExecutionSnapshots(quotes), _capture_names, quotes),
    )
    clock, charges = OwnerTimingClock(VERDICT_REACTION_MINUTES, build_session_calendar(), availability), cfg["charges"]
    books = lambda account, market: load_risk_book(root, account, market, recorded_terms(root, account))  # noqa: E731
    risk = FillDayRisk(build_risk_manager(cfg, root), books, cfg["risk_free_rate"], Black76(),
                       profile_settings(cfg, RISK_PROFILE_BOOKS).max_loss_per_trade_rs, charges)  # fmt: skip
    entries = OwnerTimingEntries(DueFill(clock, snapshots, ApprovedLimit(), charges), risk, log, VIEW_VERDICT,
                                 VERDICT_REACTION_MINUTES, now_ist)  # fmt: skip
    desk = build_exit_desk(cfg, alerts, exit_timing)  # its closed and pending events, as the daily run's own
    exits = OwnerTimingExits(clock, snapshots, desk, log, VIEW_VERDICT, VERDICT_REACTION_MINUTES, charges, now_ist)
    return entries, exits


def _capture_names(day: date) -> list[str]:
    """The day's A4 capture sidecars, committed in the repository's quote folder (A4b: quote files are in Drive)."""
    from ...quotes.recorder import DATASET
    from ...storage.wiring import QUOTES_FOLDER

    folder = Path(QUOTES_FOLDER) / DATASET / f"{day:%Y}" / f"{day:%m}"
    return sorted(p.name for p in folder.glob(f"nifty_{day:%Y%m%d}_*.meta.json"))
