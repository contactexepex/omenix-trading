"""Composition root of the market school's paper record (story MS-P1j): the fleet over the pilot's real stores,
which only this root builds: the dashcam on Drive with receipts pushed to `main`, the accounts and ticket ledger
mirrored to Drive's private area, and the counts committed by this one runner; and g's report inputs. What both the
record and the replay wire alike is `fleet_wiring.fleet_on`; a replay is `replay_wiring.build_replay_fleet`.

`school.enabled` is the only switch."""

from datetime import date, datetime
from pathlib import Path

from ..composition import build_alert_sender, build_versions
from ..config import ROOT
from ..models import now_ist
from ..research_engine.ledger import Git
from ..storage.wiring import QUOTES_FOLDER
from .accounts.wiring import build_account_sync
from .constants import SCHOOL_OFF_LINE
from .contracts.fleet import RunMode, SessionRun
from .dashcam.names import COUNTS_FOLDER
from .dashcam.wiring import build_dashcam
from .drivers.wiring import build_school_drivers
from .execution.wiring import build_fill_port
from .fleet.card_check import CardMismatchCheck
from .fleet.counts_commit import SessionFilesCommitter
from .fleet.history import RecordedSpotHistory
from .fleet.report_inputs import PreviousSlotToday, SealedDayInputs
from .fleet.runner import SchoolFleet
from .fleet.unfilled import UnfilledEntries
from .fleet_wiring import FleetStores, books_on, fleet_on
from .instructor.wiring import build_why_lines
from .instructor_step_wiring import RECEIPTS_PREFIX, build_instructor_step, instructor_files
from .quality.wiring import build_quality_gate
from .registration.counting import CARD_PATH
from .registration.wiring import build_counting_rule
from .roads.wiring import build_road_services
from .settings import school_settings

COUNTS_MESSAGE = "Counts: school session counts ({what})"


class IstClock:
    def now(self) -> datetime:
        return now_ist()


class SwitchedOff:
    """The pilot with `school.enabled` off: the school-off line, with nothing built, read or written."""

    def run(self, session: date, mode: RunMode) -> SessionRun:
        return SessionRun(session, mode, SCHOOL_OFF_LINE)


def build_fleet(cfg: dict, root: Path = ROOT) -> SchoolFleet | SwitchedOff:
    """The paper record's fleet over the pilot's real stores, or the switched-off runner: `school.enabled` is read
    here, at the pilot's entry, never by the fleet (a replay is `replay_wiring.build_replay_fleet`, which has none)."""
    if not school_settings(cfg).enabled:
        return SwitchedOff()
    committer = SessionFilesCommitter(Path(root), COUNTS_MESSAGE, (f"{COUNTS_FOLDER}/", RECEIPTS_PREFIX))
    stores = FleetStores(Path(root), build_dashcam(), committer, build_account_sync(root), IstClock(),
                         instructor_files, build_alert_sender().send)  # fmt: skip
    return fleet_on(cfg, stores, root, card_check=build_card_check(root), after_outcomes=build_instructor_step(cfg))


def build_card_check(root: Path = ROOT) -> CardMismatchCheck:
    """h's counting rule over the repository's git and D6's versions; the card's text at its commit for its version."""
    git = Git(Path(root))
    return CardMismatchCheck(build_counting_rule(git, build_versions(Path(root))),
                             lambda commit: git.committed_text(CARD_PATH, commit))  # fmt: skip


def build_report_inputs(cfg: dict, root: Path = ROOT) -> tuple[PreviousSlotToday, SealedDayInputs]:
    """g's two ports: the 08:50 plan from the previous slot, and the 20:05 day from the sealed record and counts."""
    services = build_road_services()
    drivers = build_school_drivers(cfg, root)
    gate, history = build_quality_gate(services.listing), RecordedSpotHistory(QUOTES_FOLDER)
    today = PreviousSlotToday(services.calendar, services.catalogue, services.snapshots, gate, drivers, history)
    roles = {driver.card.driver_id: driver.card.role for driver in drivers}
    return today, SealedDayInputs(build_dashcam(), root, roles, build_why_lines(cfg))


def build_unfilled_entries(cfg: dict, root: Path = ROOT) -> UnfilledEntries:
    """MS-INS part e's `unfilled`: the record's fired entries that never filled, read from the record's own stores
    (built here, read-only: the fleet is not, so a switched-off school still reads what it recorded before)."""
    dashcam = build_dashcam()
    stores = FleetStores(Path(root), dashcam, None, build_account_sync(root), IstClock())
    books = books_on(cfg, stores, build_fill_port(cfg), root)
    return UnfilledEntries(dashcam, books.account_entries, books.ticket_entries)
