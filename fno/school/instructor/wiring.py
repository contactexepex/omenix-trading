"""Composition root of `fno/school/instructor/` (story MS-INS): the path reader over c's dashcam, b's recorded
captures, d's settlement source and A7's calendar (part a); the classifier over A6's events, e's frozen cards, d's
fill port for the hold-to-expiry value, G13's rate and the frozen rules card (part c); the instructor's own store over
O9's data store and the dashcam's receipt publisher, the session run, h's counting rule over the repository's git and
D6's versions, and the "why" line source (part e)."""

import hashlib
import os
from datetime import date
from pathlib import Path

from ...books.versions import Versions
from ...composition import build_versions
from ...config import load_app_config
from ...research_data.events import read_events
from ...research_engine.ledger import Git
from ...storage.data_wiring import (
    DATA_AREA,
    RECEIPTS_FOLDER,
    REPOSITORY,
    build_data_store,
    build_drive_cache,
    receipt_folder,
)
from ...storage.manifest_commit import GitManifestRecorder
from ...storage.receipt_publisher import GitReceiptPublisher, ReceiptPublisher
from ...storage.wiring import EVENTS_FILE
from ..dashcam.names import SCHOOL_AREA
from ..dashcam.reader import VerifiedDriveReader
from ..dashcam.wiring import build_dashcam
from ..drivers.cards import CARDS_FOLDER, load_cards
from ..execution.wiring import build_fill_port, build_settlement_source
from ..registration.wiring import build_counting_rule
from ..roads.wiring import build_road_services
from ..settings import school_settings
from .adapters import CardStops, IstClock, NotYetReplayable, RecordedEventCalendar, RecordedSnapshotArchive
from .causes.classify import Classifier
from .causes.evidence import EvidenceBuilder
from .outputs.comparison import CountedComparison
from .outputs.public_counts import InstructorCountsFile
from .outputs.run import InstructorRun, SessionResult
from .outputs.store import DriveInstructorStore
from .outputs.why_line import WhyLineSource
from .ports import InstructorStore
from .reader import PathReader

WRITER = "school instructor"
RECEIPTS_MESSAGE = "Receipts: school instructor files ({what})"
RECEIPTS_LABEL = "instructor receipts"

ROOT = Path(__file__).resolve().parents[3]
RULES_CARD = ROOT / "research" / "school" / "INSTRUCTOR_V1.md"


def rules_sha256() -> str:
    return hashlib.sha256(RULES_CARD.read_bytes()).hexdigest()


def _archive(roads) -> RecordedSnapshotArchive:
    return RecordedSnapshotArchive(roads.catalogue, roads.snapshots)


def build_path_reader(publisher: ReceiptPublisher | None = None) -> PathReader:
    """`publisher`: the dashcam's way to its receipts (MS-P1j's session step passes its run's, which never fetches)."""
    roads = build_road_services()
    archive = _archive(roads)
    return PathReader(build_dashcam(publisher=publisher), archive, build_settlement_source(), roads.calendar,
                      IstClock())  # fmt: skip


def build_event_calendar() -> RecordedEventCalendar:
    return RecordedEventCalendar(read_events(EVENTS_FILE.read_text(encoding="utf-8")))


def build_classifier(config: dict | None = None) -> Classifier:
    cfg = config if config is not None else load_app_config()
    archive = _archive(build_road_services())
    stops = CardStops(load_cards(ROOT / CARDS_FOLDER).values())
    evidence = EvidenceBuilder(archive, build_event_calendar(), stops, NotYetReplayable(), build_fill_port(cfg),
                               float(cfg["risk_free_rate"]))  # fmt: skip
    return Classifier(evidence, rules_sha256())


def build_instructor_store(run_id: str | None = None, env=os.environ,
                           publisher: ReceiptPublisher | None = None) -> DriveInstructorStore:  # fmt: skip
    """Drive through the owner's credential, receipts beside the dashcam's in the school's receipt folder, committed
    and pushed by this store unless `publisher` says otherwise (MS-P1j's session step: by its run's counts commit)."""
    publisher = publisher or _instructor_publisher()
    reader = VerifiedDriveReader(build_drive_cache(env), DATA_AREA)
    return DriveInstructorStore(build_data_store(WRITER, run_id, env), publisher, reader)


def _instructor_publisher() -> GitReceiptPublisher:
    folder = REPOSITORY / RECEIPTS_FOLDER / DATA_AREA / SCHOOL_AREA
    recorder = GitManifestRecorder(REPOSITORY, folder, message=RECEIPTS_MESSAGE, label=RECEIPTS_LABEL)
    return GitReceiptPublisher(recorder, receipt_folder(), REPOSITORY)


def build_instructor_run(config: dict, store: InstructorStore | None = None,
                         publisher: ReceiptPublisher | None = None) -> InstructorRun:  # fmt: skip
    """`store` and `publisher`: MS-P1j's session step passes its deferred store and its run's receipts."""
    first_counted = school_settings(config).first_counted
    return InstructorRun(build_path_reader(publisher), build_classifier(config), store or build_instructor_store(),
                         float(config["risk_free_rate"]), rules_sha256(), first_counted)  # fmt: skip


def build_comparison(versions: Versions | None = None) -> CountedComparison:
    counting = build_counting_rule(Git(ROOT), versions or build_versions(ROOT))
    return CountedComparison(counting, load_cards(ROOT / CARDS_FOLDER), rules_sha256())


def build_why_lines(config: dict | None = None) -> WhyLineSource:
    """For MS-P1j's wiring: g's 20:05 section reads `lines(session)` through a `why` port in its day inputs (agreed
    with j's builder, 23 Oct 2026). `config` is accepted for that wiring's shape; the store needs none."""
    return WhyLineSource(build_instructor_store())


def run_instructor_session(config: dict, session: date, write: bool = True) -> SessionResult:
    """MS-P1j's one entry point, after the session's outcomes file is sealed and before its counts commit: attribute,
    classify, write the instructor's files and its public counts file (which j's commit then takes)."""
    result = build_instructor_run(config).for_session(session, write)
    if write:
        build_counts_file().write(session, result.classifications)
    return result


def build_counts_file() -> InstructorCountsFile:
    return InstructorCountsFile(REPOSITORY)
