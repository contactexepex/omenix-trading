"""Story G11, collecting the AI books' v4 day (response 272), run in forecast-capture's collect slot after the 15:10
deadline and its reveals: for each book, read its submission at v4's paths with GitHub's receipt times, judge it with
F1/G5's own `outcome.judge` under v4's terms (15:10, reveal 15:10:10-15:30) against the labels, questions and envelope
the fire logged, mark exposures, and write its audit file once. The rows come later, from the settled audit
(`v4_settle.py`): a written row never changes, so it waits for the transcript audit.

- **The fire log is the record of what each book was given** (review of dfb26381): the input is never rebuilt here,
  because the files it is built from (closes, A16's rows) can still change after the fire and a write-once verdict
  must not depend on when collect runs. A book's answer must carry the logged labels (its input's hash among them).
- A session the fire never ran (no fire log, a released pack, from the v4 go-live date) is collected as `not_fired`
  for every registered question, so it is a miss, never a gap (design item 7). **But a missing log while a
  commitment of that day exists waits** ("awaiting the fire log"; the fire uploads its log as a run artifact when its
  push fails, so it can be restored) for `LOST_LOG_SESSIONS` sessions, then that book is `invalid` (a miss): what it
  was given can no longer be shown. The log is read as first committed: a later edit changes no verdict.
- No released pack: nothing is collected (no row; the look's reconciliation leaves `system_late` days out).
- The release record is read here, never taken from the fire log: its SHA is stored in the audit, and the rows' pack
  guard checks the pack each book was given against it (two sources, not one).
- **Every session since go-live still without both audits is collected again** (G11 C19): a day whose GitHub receipt
  time cannot be found yet (`ReceiptUnknown`) gets no verdict and no audit (never a guessed time; exposure needs both
  books' times, so the whole day waits), is printed "awaiting GitHub's receipt" and is retried by every later collect;
  a session the collect itself never ran is caught up the same way. G8's look refuses while such a day has no row.
- **From the AI slots' own start** (judge 586 F1): collect begins at the earlier of the go-live date and the AI slots'
  earliest `effective_start`, so a session before go-live is a `not_fired` miss ("before the AI books' v4 go-live"),
  never a gap that would stop G8's looks.
- **Today waits for its reveals:** before 15:30 IST, today is collected only once every fired book has revealed."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from ..constants import AI_BOOKS, BOOK2_HYBRID
from ..v4_pack.release import NotReleased, ReleasedPacks
from .envelope import Envelope
from .history import RepoHistory
from .outcome import INVALID, NOT_FIRED, Outcome, judge, mark_exposures
from .receipts import PushReceipts, ReceiptUnknown
from .record_writer import audit_text
from .run_terms import FORECAST_PROTOCOL_V4, V4_TERMS
from .submissions import read_submission
from .v4_book_inputs import V4BookInputs
from .v4_go_live import BEFORE_GO_LIVE, first_collected_day
from .versions import current_version, version_by_label

LINE = "Omenix F&O AI forecasts v4 (GitHub Actions): {day}: {result}"
AWAITING_RECEIPT = "awaiting GitHub's receipt ({why}); nothing written, the next collect retries it"
AWAITING_LOG = "awaiting the fire log: {book}'s commitment exists but no fire log does; nothing written, retried"
TOO_EARLY = "too early: not every fired book has revealed and it is before {by:%H:%M} IST; the next collect takes it"
NO_LOG = "the v4 fire left no log for this session (it never ran, or its log was lost before any book committed)"
LOST_LOG_SESSIONS = 3  # a commitment without a fire log waits this many sessions for the log to be restored
LOG_LOST = "the fire log was lost and not restored within {sessions} sessions: what the book was given is unknown"
NO_ENVELOPE = "the fire log holds no envelope for Hybrid: its answer cannot be checked"
NO_LABELS = "the fire log holds no labels for this book (a log from before the labels were logged)"


class Waiting(Exception):
    """The day cannot be judged yet; nothing is written and a later collect retries it."""


@dataclass
class V4BookCollector:
    root: Path
    history: RepoHistory
    receipts: PushReceipts
    inputs: V4BookInputs
    released: Callable[[], ReleasedPacks]  # only the release record is read: the books' inputs are in the fire log
    clock: Callable[[], datetime]
    live_from: date | None
    sessions: Callable[[date, date], list[date]]  # v4's scored sessions from the first day to the last, both included

    def collect(self, day: date) -> list[str]:
        first = first_collected_day(self.inputs.registry, self.live_from)
        if first is None or day < first:
            return [LINE.format(day=day, result="v4 is not live yet; nothing collected")]
        days = [d for d in self.sessions(first, day) if d == day or not self._collected(d)]
        return [line for d in days for line in self._collect_day(d)]

    def _today_too_early(self, day: date, log: dict) -> bool:
        if self.clock() >= V4_TERMS.reveal_deadline(day):
            return False
        fired = [book for book, entry in log["books"].items() if entry["fired"]]
        return not all(self.history.first_commit_adding(V4_TERMS.reveal_path(day, b)) for b in fired)

    def _collected(self, day: date) -> bool:
        return all((self.root / V4_TERMS.audit_path(day, book)).is_file() for book in AI_BOOKS)

    def _collect_day(self, day: date) -> list[str]:
        try:
            packs = self.released()
            release = packs.release(day)
            packs.pack_bytes(release)  # refuses a system_late record and verifies the pack (`release` does neither)
        except NotReleased as missing:
            return [LINE.format(day=day, result=f"no released pack ({missing}); nothing collected (no row)")]
        try:
            log = self._log(day, release.pack_sha256)
            if self._today_too_early(day, log):
                raise Waiting(TOO_EARLY.format(by=V4_TERMS.reveal_by))
            outcomes = {book: self._outcome(day, book, entry) for book, entry in log["books"].items()}
        except ReceiptUnknown as unknown:
            return [LINE.format(day=day, result=AWAITING_RECEIPT.format(why=unknown))]
        except Waiting as waiting:
            return [LINE.format(day=day, result=str(waiting))]
        mark_exposures(outcomes)
        lines = []
        for book, outcome in outcomes.items():
            written = self._write(day, outcome, log["books"][book], release.pack_sha256)
            lines.append(LINE.format(day=day, result=f"{book} {outcome.status}: {written}"))
        return lines

    def _log(self, day: date, released_sha256: str) -> dict:
        """The fire log; a session the fire never ran, or ran while no pack could be read, gets one built here: every
        book not_fired, so a released day is never left without a row."""
        log = self._first_log(day)
        if "books" in log:
            return log
        committed = [b for b in AI_BOOKS if self.history.first_commit_adding(V4_TERMS.commitment_path(day, b))]
        if committed and len(self.sessions(day, self.clock().date())) <= LOST_LOG_SESSIONS:
            raise Waiting(AWAITING_LOG.format(book=committed[0]))
        return {"books": {b: self._lost(day, b, released_sha256, b in committed) for b in AI_BOOKS}}

    def _first_log(self, day: date) -> dict:
        """The fire log as the commit that first added it holds it (a later edit changes no verdict); the checkout's
        file only while no commit has it yet."""
        path = V4_TERMS.fired_path(day)
        commit = self.history.first_commit_adding(path)
        text = self.history.committed_text(path, commit) if commit else None
        if text is None and (self.root / path).is_file():
            text = (self.root / path).read_text(encoding="utf-8")
        return json.loads(text) if text else {}

    def _lost(self, day: date, book: str, sha: str, committed: bool) -> dict:
        """A day without a fire log: not fired, or (a commitment exists, past the wait) one whose input is unknown."""
        version = current_version(book, FORECAST_PROTOCOL_V4)
        live = self.live_from is not None and day >= self.live_from
        reason = NO_LOG if live else BEFORE_GO_LIVE.format(live_from=self.live_from or "not set")
        entry = {"version": version.label, "fired": False, "stop_rule": False, "pack_sha256": sha,
                 "questions": self.inputs.questions(version, day), "reason": reason}  # fmt: skip
        return entry | ({"fired": True, "log_lost": True} if committed else {})

    def _outcome(self, day: date, book: str, entry: dict) -> Outcome:
        version, questions = version_by_label(entry["version"]), tuple(entry.get("questions", ()))
        if not entry["fired"]:
            outcome = Outcome(book, NOT_FIRED, version.label, questions)
            outcome.withdraw(NOT_FIRED, f"the routine was not fired: {entry.get('reason', '')}")
            return outcome
        if entry.get("log_lost"):
            return _invalid(book, version.label, questions, LOG_LOST.format(sessions=LOST_LOG_SESSIONS))
        if "labels" not in entry:
            return _invalid(book, version.label, questions, NO_LABELS)
        if book == BOOK2_HYBRID and not entry.get("envelope"):
            return _invalid(book, version.label, questions, NO_ENVELOPE)
        envelope = Envelope.from_json(entry["envelope"]) if entry.get("envelope") else None
        submission = read_submission(self.history, self.receipts, day, book, V4_TERMS)
        unknown = [p.receipt_problem for p in (submission.commitment, submission.reveal) if p and p.received_at is None]
        if unknown:
            raise ReceiptUnknown(unknown[0])
        return judge(book, day, submission, entry["labels"], envelope, version, V4_TERMS, questions)

    def _write(self, day: date, outcome: Outcome, fired: dict, released_sha256: str) -> str:
        """Once; the release record's SHA, read here and not from the fire log, is what the rows' pack guard checks."""
        file = self.root / V4_TERMS.audit_path(day, outcome.book)
        if file.is_file():
            return "already collected (the first collection stands)"
        file.parent.mkdir(parents=True, exist_ok=True)
        v4 = {"collected_at": self.clock().isoformat(), "released_sha256": released_sha256}
        file.write_text(audit_text(day, outcome, fired, v4), encoding="utf-8")
        return "collected; its rows land once its audit settles"


def _invalid(book: str, label: str, questions: tuple[str, ...], why: str) -> Outcome:
    outcome = Outcome(book, INVALID, label, questions)
    outcome.withdraw(INVALID, why)
    return outcome
