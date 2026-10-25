"""Composition root of the daily packs (story E2): the common pack's inputs (A4 snapshot, session calendar, official
closes, events), D2's opportunity code with the playbook, and the private pack's folders. Apart from `wiring.py`
(story E4's fills), so each story's parts are wired in one place."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

from ..config import ROOT
from ..constants import BOOK1_RULES
from .common_pack import CommonPackBuilder
from .packs import WrittenPacks
from .private_pack import PrivatePackBuilder

PACKED_BOOKS = (BOOK1_RULES,)  # the daily run also packs each live AI book (story F1t)
SHEETS: dict = {}  # story E2e: book -> its BookSheet (F5's Book 2, F6's Book 3 add their lines)


def build_common_pack_builder(root: Path = ROOT) -> CommonPackBuilder:
    from ..composition import build_session_calendar
    from ..forecast.closes_source import CommittedClosesFile
    from ..playbook.opportunities import OpportunityFinder
    from ..playbook.wiring import build_playbook_loader
    from ..quotes.recorder import DATASET
    from ..research_data.events import read_events
    from ..research_engine.cycles import TradingDays
    from ..storage.wiring import EVENTS_FILE, PANEL_FOLDER, build_quote_store
    from .opportunity_set import OpportunitySet
    from .reference_inputs import ClosesInput, EventsInput, SessionInput
    from .snapshot_inputs import SnapshotInput

    calendar = build_session_calendar()
    events = tuple(read_events(EVENTS_FILE.read_text(encoding="utf-8")))
    inputs = (
        SnapshotInput(build_quote_store(), DATASET),  # the same snapshot dataset E4 fills from
        SessionInput(calendar),
        ClosesInput(CommittedClosesFile(PANEL_FOLDER / "warmup_closes.csv")),
        EventsInput(events, EVENTS_FILE.relative_to(ROOT).as_posix()),
    )
    return CommonPackBuilder(
        inputs, OpportunitySet(OpportunityFinder(TradingDays(calendar))), build_playbook_loader(root)
    )


def build_private_pack_builder(root: Path = ROOT) -> PrivatePackBuilder:
    return PrivatePackBuilder(root)


def build_packs(root: Path = ROOT, refresh: Callable[[], None] = lambda: None, files=None, alerts=None,
                books: Sequence[str] = PACKED_BOOKS) -> WrittenPacks:  # fmt: skip
    """The day's common pack and each packed book's private pack, written once under `journal/`; the private packs are
    kept in Drive (story E2c), with only their `.sha256` committed. `alerts`: the caller's one sender (the daily run's
    reported sender, story O1); a command run alone gets the app's. `books`: the run's books (story F1t)."""
    from ..composition import DESK_DECISION_TIME, build_alert_sender
    from .pack_store import PackStore
    from .wiring import build_private_files

    keep, alerts = (files or build_private_files(root)).push, alerts or build_alert_sender()
    return WrittenPacks(build_common_pack_builder(root), build_private_pack_builder(root), PackStore(root),
                        DESK_DECISION_TIME, tuple(books), refresh, keep, SHEETS, alerts,
                        tuple(b for b in books if b != BOOK1_RULES))  # fmt: skip  # F1t: AI books refused alone
