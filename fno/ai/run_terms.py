"""Story G11, the terms of one protocol's AI run (response 272 addendum 3): where a book's commitment, reveal, audit and
fire log live, when GitHub must have received the commitment, and when its reveal may be read and must be in (the
questions are the day's, in its pointer). One class, two instances: F1/G5's chain takes the terms (default v2's, so
every v2 caller is unchanged) instead of fixing v2 everywhere, and no copy of the chain exists. Standard library only
(the book side reads it).

v4's deadline is `terms.V4_DEADLINE`, the constant G10's `on_time` (`fno/v4_pack/commitment.py`) compares with: the
same rule, from the same constant (a test checks both agree at 15:10:00 and 15:10:01)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time

from ..forecast.schema_v2 import GENERATION_DEADLINE
from ..forecast_v4.terms import V4_DEADLINE
from ..models import IST
from .paths import AI_FOLDER, AI_V4_FOLDER, audit_path, commitment_path, fired_path, reveal_path, transcript_audit_path

FORECAST_PROTOCOL_V2, FORECAST_PROTOCOL_V4 = "v2", "v4"  # which protocol a run and a book version answer
REVEAL_FROM = time(15, 15, 10)  # v2: 10 s after the deadline, so a little clock drift cannot open an answer early
V4_REVEAL_FROM = time(15, 10, 10)  # v4: the same 10 s after its deadline
REVEAL_DEADLINE = time(15, 30)  # both: the collection keeps forecast-capture's slot


@dataclass(frozen=True)
class RunTerms:
    protocol: str
    folder: str  # the AI books' files of this protocol: submissions, audits, fire logs
    deadline: time  # GitHub's receipt of the commitment, IST
    reveal_from: time  # no answer is readable before every commitment is in (a few seconds of clock drift)
    reveal_by: time  # the collection waits for reveals until then (15:30 for both: collect keeps its slot)
    books_key: str | None = None  # where a fire log keeps its books' entries: v2's log is them, v4's under "books"

    def commitment_path(self, day: date, book: str) -> str:
        return commitment_path(day, book, self.folder)

    def reveal_path(self, day: date, book: str) -> str:
        return reveal_path(day, book, self.folder)

    def audit_path(self, day: date, book: str) -> str:
        return audit_path(day, book, self.folder)

    def fired_path(self, day: date) -> str:
        return fired_path(day, self.folder)

    def transcript_audit_path(self, day: date, book: str) -> str:
        return transcript_audit_path(day, book, self.folder)

    @property
    def draws_folder(self) -> str:
        """The weekly audit draws of this protocol's runs (one draw per protocol: v4's sessions are drawn apart)."""
        return f"{self.folder}/draws"

    def fired_books(self, log: dict) -> dict:
        """book -> its entry in a fire log (a v4 log with no released pack has none)."""
        return log if self.books_key is None else log.get(self.books_key, {})

    def receipt_deadline(self, day: date) -> datetime:
        return datetime.combine(day, self.deadline, tzinfo=IST)

    def reveal_opens(self, day: date) -> datetime:
        return datetime.combine(day, self.reveal_from, tzinfo=IST)

    def reveal_deadline(self, day: date) -> datetime:
        return datetime.combine(day, self.reveal_by, tzinfo=IST)


V2_TERMS = RunTerms(FORECAST_PROTOCOL_V2, AI_FOLDER, GENERATION_DEADLINE, REVEAL_FROM, REVEAL_DEADLINE)
V4_TERMS = RunTerms(FORECAST_PROTOCOL_V4, AI_V4_FOLDER, V4_DEADLINE, V4_REVEAL_FROM, REVEAL_DEADLINE, books_key="books")
