"""One session's market read-model run (stories P6, P7): archive the session's files (when given a step for it), build
the rows, validate every block against the pinned W11 contract, publish all of them at once and read them back. Any
failure stops the run before anything is published, prints the reason and alerts #fno-desk; the previous publication
stays current. Every run leaves a run-status row: `running` at the start, then `published`, `failed` with a reason
code, or `skipped` (P7). It prints only counts and hashes, never a credential."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import date

from ..alerts.sender import AlertSender
from ..research_data.calendar import SessionCalendar
from .contract import ContractBroken, PinnedContract
from .home_blocks import FiguresNotComputed
from .page_holds import held_lines
from .publication import Publication, PublicationBuilder, hashes
from .publication_inputs import PublicationInputsFile
from .publisher import PublishFailed, ReadModelPublisher
from .run_status import (
    ARCHIVE_INCOMPLETE,
    CONTRACT_CHANGED,
    CRASHED,
    FAILED,
    FIGURES_NOT_COMPUTED,
    NOT_A_SESSION,
    PUBLISHED,
    READ_BACK_MISMATCH,
    SCHEMA_INVALID,
    SKIPPED,
    Outcome,
    RunStatusRecorder,
    database_code,
)  # fmt: skip
from .session_rows import IncompleteSession, SessionRowsBuilder

NOT_A_SESSION_LINE = "{day}: not a trading day, nothing to publish"
PUBLISHED_LINE = "{day}: published {count} blocks as {publication_id} to {publisher} ({added} rows added)"
READ_BACK = "read back {count} pages of {publication_id}: every payload SHA-256 equals the built records"
PAGE_HASH = "    {page_key} {sha256}"
FAMILY_HASH = "    {family} {count} pages, SHA-256 of their hashes {sha256}"
READ_BACK_DIFFERS = "read back {publication_id}: {pages} differ from the built records"
FAILED_LINE = (
    "Omenix F&O market read models for {day} NOT published ({step}): {reason}. The previous publication stays current."
)
DAMAGED_PIN = "the pinned W11 contract copy differs from its pin: {files}"
CRASH_REASON = "the run stopped on an unexpected error; see its log"

Prepare = Callable[[date], str | None]  # archives the session's files; the first problem, or None


class Stopped(Exception):
    def __init__(self, step: str, code: str, reason: str):
        super().__init__(reason)
        self.step, self.code, self.reason = step, code, reason


class MarketRun:
    def __init__(
        self,
        calendar: SessionCalendar,
        contract: PinnedContract,
        rows: SessionRowsBuilder,
        publications: PublicationBuilder,
        publisher: ReadModelPublisher,
        alerts: AlertSender,
        status: RunStatusRecorder,
        run_id: Callable[[], str],
        inputs: PublicationInputsFile | None = None,
    ):
        self.calendar, self.contract, self.rows = calendar, contract, rows
        self.publications, self.publisher, self.alerts = publications, publisher, alerts
        self.status, self.run_id, self.inputs = status, run_id, inputs

    def run(self, day: date, prepare: Prepare | None = None) -> tuple[int, list[str]]:
        """(exit code, lines to print). The status row is written whatever happens; a crash is recorded, then raised."""
        run_id = self.run_id()
        notes = [self.status.start(run_id, day)]
        try:
            code, lines, outcome = self._attempt(day, prepare)
        except Exception:
            self.status.finish(run_id, Outcome(FAILED, CRASHED, CRASH_REASON))
            raise
        notes.append(self.status.finish(run_id, outcome))
        return code, lines + [note for note in notes if note]

    def _attempt(self, day: date, prepare: Prepare | None) -> tuple[int, list[str], Outcome]:
        if not self.calendar.is_session(day):
            line = NOT_A_SESSION_LINE.format(day=day)
            return 0, [line], Outcome(SKIPPED, NOT_A_SESSION, line)
        try:
            publication, added = self._publish(day, prepare)
        except Stopped as stop:
            message = FAILED_LINE.format(day=day, step=stop.step, reason=stop.reason)
            return 1, [message, self.alerts.send(message)], Outcome(FAILED, stop.code, message)
        line = PUBLISHED_LINE.format(day=day, count=len(publication.records), publication_id=publication.publication_id,
                                     publisher=self.publisher.name, added=added)  # fmt: skip
        held = held_lines(day, publication.held, publication.broken, self.contract.version)  # story P11
        alerted = [sent for h in held for sent in (h, self.alerts.send(h))]
        stored = hashes(publication)
        read_back = READ_BACK.format(count=len(stored), publication_id=publication.publication_id)
        inputs = self.inputs.record(publication) if self.inputs else []
        lines = [line, *alerted, read_back, *hash_lines(stored), *inputs]
        return 0, lines, Outcome(PUBLISHED, reason="; ".join(held) or None, publication_id=publication.publication_id)

    def _publish(self, day: date, prepare: Prepare | None) -> tuple[Publication, int]:
        problem = prepare(day) if prepare else None
        if problem:
            raise Stopped("archived files", ARCHIVE_INCOMPLETE, problem)
        changed = self.contract.changed_files()
        if changed:
            raise Stopped("contract", CONTRACT_CHANGED, DAMAGED_PIN.format(files=", ".join(changed)))
        try:
            publication = self.publications.build(self.rows.build(day), self.publisher.current)
        except IncompleteSession as exc:
            raise Stopped("archived files", ARCHIVE_INCOMPLETE, str(exc)) from exc
        except ContractBroken as exc:
            raise Stopped("W11 schema", SCHEMA_INVALID, str(exc)) from exc
        except FiguresNotComputed as exc:
            raise Stopped("F&O figures", FIGURES_NOT_COMPUTED, str(exc)) from exc
        except PublishFailed as exc:  # the current publication could not be read for a held page (story P11)
            raise Stopped("publish", database_code(exc.failure_class), str(exc)) from exc
        try:
            added = self.publisher.publish(publication)
            stored = self.publisher.stored(publication.publication_id)
        except PublishFailed as exc:
            raise Stopped("publish", database_code(exc.failure_class), str(exc)) from exc
        built = hashes(publication)
        if stored != built:
            differing = sorted(k for k in built.keys() | stored.keys() if built.get(k) != stored.get(k))
            reason = READ_BACK_DIFFERS.format(publication_id=publication.publication_id, pages=", ".join(differing))
            raise Stopped("read-back", READ_BACK_MISMATCH, reason)
        return publication, added


def hash_lines(stored: dict[str, str]) -> list[str]:
    """One line per block: its page's SHA-256, or for a block stored one page per parameter (`<block>:<parameter>`,
    P9) its page count and the SHA-256 of its pages' keys and hashes, so a day's log stays short."""
    families: dict[str, list[str]] = {}
    for key in sorted(stored):
        families.setdefault(key.split(":", 1)[0], []).append(key)
    lines = []
    for family, keys in families.items():
        if keys == [family]:
            lines.append(PAGE_HASH.format(page_key=family, sha256=stored[family]))
        else:
            joined = "\n".join(f"{k} {stored[k]}" for k in keys).encode()
            lines.append(FAMILY_HASH.format(family=family, count=len(keys), sha256=hashlib.sha256(joined).hexdigest()))
    return lines
