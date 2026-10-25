"""Composition root of the instructor's session step in the paper record (story MS-P1j with MS-INS part e; judge 523,
orchestrator's ruling: one committer per run). The step's work, on a thread under its time limit, runs part e's session
run over a deferred store and its run's receipts, so it only reads and computes; its writes (the instructor's two
Drive files with their receipts, then its counts file, in part e's order) run on the run's own thread, and the run's
counts commit takes the files `instructor_files` names."""

from datetime import date
from functools import partial

from ..composition import build_alert_sender
from ..storage.data_wiring import DATA_AREA, RECEIPTS_FOLDER, REPOSITORY, receipt_folder
from ..storage.receipt_publisher import RemoteReceipts
from .fleet.deferred_store import DeferredInstructorStore
from .fleet.run_receipts import RunReceipts
from .fleet.session_hook import StagedSessionStep, Writes
from .instructor.contracts import Classification
from .instructor.outputs.public_counts import counts_path
from .instructor.outputs.store import INSTRUCTOR_FOLDER, instructor_path
from .instructor.ports import InstructorKind
from .instructor.wiring import build_counts_file, build_instructor_run, build_instructor_store

INSTRUCTOR = "instructor"
SESSION_KINDS = (InstructorKind.ATTRIBUTION, InstructorKind.CAUSES)  # a session run's files; `paired` is the review's
RECEIPTS_PREFIX = f"{RECEIPTS_FOLDER}/{DATA_AREA}/{INSTRUCTOR_FOLDER}/"  # where `instructor_files` names its receipts


def build_instructor_step(cfg: dict) -> StagedSessionStep:
    receipts = RunReceipts(RemoteReceipts(receipt_folder(), REPOSITORY))
    return StagedSessionStep(INSTRUCTOR, partial(instructor_work, cfg, receipts), build_alert_sender().send,
                             prepare=receipts.refresh)  # fmt: skip


def instructor_work(cfg: dict, receipts: RunReceipts, session: date) -> Writes:
    """On the step's thread: part e's session run, reading through the run's receipts, writing nothing."""
    store = DeferredInstructorStore(build_instructor_store(publisher=receipts))
    result = build_instructor_run(cfg, store, receipts).for_session(session, write=True)
    return partial(write_instructor, store, session, result.classifications)


def write_instructor(store: DeferredInstructorStore, session: date, classifications: tuple[Classification, ...]):
    """On the run's own thread: the Drive files and their receipts first, then the counts file."""
    store.flush()
    build_counts_file().write(session, classifications)


def instructor_files(session: date) -> tuple[str, ...]:
    """What the run's counts commit takes for the step: its counts file and its session files' receipts."""
    receipts = receipt_folder()
    named = (receipts.file_for(f"{DATA_AREA}/{instructor_path(session, kind)}") for kind in SESSION_KINDS)
    return (str(counts_path(session)), *(file.relative_to(REPOSITORY).as_posix() for file in named))
