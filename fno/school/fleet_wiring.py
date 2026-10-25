"""The fleet's shared composition (story MS-P1j): what both roots wire alike, over the stores they hand in. It reads
b's roads and quality gate, e's drivers, d's laws, fills and margin, and the 15:15 capture, all read-only; it builds
no store that writes. The record root (`wiring.py`) hands in the pilot's real stores; the replay root
(`replay_wiring.py`) hands in scratch stores under its folder and cannot reach the real ones (judge 512: by
construction, not by a mode switch)."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ..config import ROOT
from ..storage.wiring import QUOTES_FOLDER
from .accounts.names import school_root
from .accounts.reviews import REVIEWS_FILE, ReviewFile
from .accounts.school_accounts import SchoolAccounts
from .accounts.wiring import build_account_port
from .contracts.accounts import FillPort
from .contracts.clock import Clock
from .contracts.dashcam import DashcamStore
from .drivers.wiring import build_school_drivers
from .execution.wiring import build_capture_1515, build_fill_port
from .fleet.books import Books
from .fleet.card_check import no_check
from .fleet.counts_file import CountsCommitter, SessionCounts
from .fleet.entry_mids import DashcamEntryMids
from .fleet.history import RecordedSpotHistory
from .fleet.runner import SchoolFleet
from .fleet.session_hook import no_step
from .quality.wiring import build_quality_gate
from .roads.wiring import build_road_services
from .safety.wiring import build_margin, build_safety_laws
from .settings import school_settings
from .tickets.book import TicketBook, TicketLedger

TICKETS_FOLDER = "tickets"  # journal/school/tickets: the ticket ledger, apart from every driver account


@dataclass(frozen=True)
class FleetStores:
    """Where a run writes: `home` holds the accounts, the ticket ledger and the counts files."""

    home: Path
    dashcam: DashcamStore
    committer: CountsCommitter | None
    sync: object | None  # d's account mirror to Drive's private area; None writes locally only
    clock: Clock
    counts_extra: Callable[[date], tuple[str, ...]] = lambda session: ()  # others' files the counts commit takes
    alert: Callable[[str], object] = lambda line: None  # #fno-desk for the record: a refused counts commit, by name


def books_on(cfg: dict, stores: FleetStores, fills: FillPort, root: Path = ROOT) -> Books:
    """The driver accounts and the ticket ledger under `stores.home`, filled through `fills`: one construction for
    the pilot's roots and the simulator's practice root, which passes its own fill port."""
    settings = school_settings(cfg)
    accounts = build_account_port(cfg, settings, stores.home, stores.sync)
    tickets = SchoolAccounts(school_root(stores.home) / TICKETS_FOLDER, settings.account_rs, settings.brake_rs,
                             cfg["charges"], ReviewFile(Path(root) / REVIEWS_FILE), stores.sync)  # fmt: skip
    return Books(accounts, accounts, TicketBook(fills, TicketLedger(tickets)), tickets, fills)


def fleet_on(cfg: dict, stores: FleetStores, root: Path = ROOT, card_check=no_check,
             after_outcomes=no_step) -> SchoolFleet:  # fmt: skip
    """`card_check`: the record's comparison-card mismatch check (MS-P1j runbook); `after_outcomes`: the record's step
    after the outcomes' seal (the instructor's run). A replay passes neither."""
    settings = school_settings(cfg)
    books = books_on(cfg, stores, build_fill_port(cfg), root)
    services, margin = build_road_services(), build_margin(cfg)
    return SchoolFleet(
        settings, services.catalogue, services.snapshots, build_quality_gate(services.listing),
        RecordedSpotHistory(QUOTES_FOLDER), build_school_drivers(cfg, root),
        lambda marks: build_safety_laws(cfg, settings, marks, margin), books, stores.dashcam,
        SessionCounts(stores.home, stores.committer, stores.counts_extra, stores.alert),
        build_capture_1515(root).for_session, DashcamEntryMids(stores.dashcam), stores.clock, card_check=card_check,
        after_outcomes=after_outcomes,
    )  # fmt: skip
