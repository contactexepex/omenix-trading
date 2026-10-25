"""Composition root of the paper desk's fills, exits and settlements (stories E4 and E7): the only place that picks
the quote store the execution snapshots are read from, the charges model's table, the alert sender, NSE's final
settlement prices and the account writer. Swapping any of them changes this file only. Nothing here can place an
order: the desk reads recorded quotes and published NSE files, never a broker."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from ..alerts.sender import AlertSender
from ..books.lock import DEFAULT_LEASE_SECONDS
from ..composition import build_alert_sender, open_account_writer
from ..config import ROOT
from ..playbook.schema import Strategy
from ..risk.inputs import Market, TradeTerms
from ..storage.wiring import build_nse_fo_library, build_quote_store
from .entries import EntryDesk
from .exit_timing import ExitTiming
from .exits import ExitDesk
from .private_files import PrivateFiles, PrivateFilesUnavailable
from .records import DeskJournal
from .settlement import NseFinalSettlement
from .shadow_books import JournalShadowBooks, start_shadow_accounts
from .snapshot import ExecutionSnapshotSource, RecordedExecutionSnapshots

SETTINGS_MISSING = "the private paper records need Drive's owner settings ({settings})"


def build_execution_snapshots(folder: Path | None = None) -> ExecutionSnapshotSource:
    """A4's recorded captures (the repository's quote folder), read by snapshot ID."""
    return RecordedExecutionSnapshots(build_quote_store(folder))


def build_entry_desk(cfg: dict) -> EntryDesk:
    return EntryDesk(cfg["charges"])


def build_exit_desk(cfg: dict, alerts: AlertSender | None = None, timing: ExitTiming | None = None) -> ExitDesk:
    """Exits at the execution snapshot's quotes; expired legs settled from NSE's daily F&O files (A2's library).
    `alerts`: the daily run's one sender (story O1), so an unsent exit alert is printed for the routine. `timing`:
    story E8's owner-timing exits (E4's close at the snapshot when none is given)."""
    return ExitDesk(cfg["charges"], alerts or build_alert_sender(), NseFinalSettlement(build_nse_fo_library()),
                    timing=timing)  # fmt: skip


def build_shadow_books(market: Market, terms: Callable[[str], Mapping[str, TradeTerms]], root: Path = ROOT
                       ) -> JournalShadowBooks:  # fmt: skip
    """D2's `ShadowBooks` for one day: each research candidate's own account under `journal/shadow/`, valued on that
    account's own terms (`terms(account)`, story R3)."""
    return JournalShadowBooks(root, market, terms)


def start_shadow_books(strategies: Iterable[Strategy], day: date, root: Path = ROOT, files=None) -> list[str]:
    """Open every candidate's shadow account once; run before the day's evaluation (E3). With `files`, each new
    account is kept in Drive (story E2c)."""
    return start_shadow_accounts(strategies, day, lambda name: open_account_writer(name, root, files=files))


@contextmanager
def open_desk_journal(
    book: str, root: Path = ROOT, lease_seconds: float = DEFAULT_LEASE_SECONDS, files=None
) -> Iterator[DeskJournal]:
    """The book's desk journal under its single-writer lock (E1): `AccountBusy` if another writer holds it. With
    `files` (story E2c), the account is pulled from Drive and pushed back."""
    with open_account_writer(book, root, lease_seconds, files) as writer:
        yield DeskJournal(writer)


def build_private_files(root: Path = ROOT, wrap=None) -> PrivateFiles:
    """Story E2c: the private paper records in Drive's `paper` area, written as the owner. Drive is signed in to only at
    the first pull or push, so building needs no Drive; missing settings then stop that step, named. `wrap` decorates
    the store (story E8: its step's pulls are time-capped)."""
    from ..constants import PAPER_AREA
    from ..storage.index_store import DriveIndexStore
    from ..storage.wiring import OWNER_UPLOAD_SETTINGS, build_owner_drive

    def store() -> DriveIndexStore:
        drive = build_owner_drive()
        if drive is None:
            raise PrivateFilesUnavailable(SETTINGS_MISSING.format(settings=", ".join(OWNER_UPLOAD_SETTINGS)))
        opened = DriveIndexStore(drive, PAPER_AREA)
        return wrap(opened) if wrap else opened

    return PrivateFiles(store, root)


def download_private_records(day: date | None = None, root: Path = ROOT) -> PrivateFiles:
    """Story E2c: the one shared download before a command reads the paper accounts (and, with `day`, the books'
    private packs of that day). `PrivateFilesUnavailable` when Drive cannot be read: the command stops, named."""
    files = build_private_files(root)
    files.download(day)
    return files
