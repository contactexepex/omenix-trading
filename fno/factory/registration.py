"""G0 registration (story R1): an idea card becomes a ledger trial (B4's guard) and its first gate-log row, `idea`.

Both rows and the card are committed together, so nothing else may be staged. Cards registered by hand before this
code (R2, FT1, B0) get a back-filled `idea` row dated by their ledger row and labelled back-filled; no later gate is
back-filled."""

from __future__ import annotations

from datetime import date
from typing import Protocol

from ..research_engine.ledger import LEDGER_FILE, Ledger
from .card import IdeaCard
from .constants import BACKFILLED, GATES_FILE, IDEA_KIND, Gate, Outcome
from .gate_log import GateLog, GateRow


class RegistrationError(ValueError):
    """The card is not registered; nothing was written."""


class RegistrationGit(Protocol):
    def head(self) -> str: ...

    def staged_paths(self) -> list[str]: ...

    def first_commit_containing(self, text: str, path: str) -> str | None: ...


class IdeaRegistration:
    def __init__(self, ledger: Ledger, gates: GateLog, git: RegistrationGit):
        self.ledger, self.gates, self.git = ledger, gates, git

    def register(self, card: IdeaCard, today: date) -> tuple[str, ...]:
        """Writes the ledger row and the `idea` row; returns the files to commit together. Every git read comes before
        the first write. A rerun after a stop between the two writes (its ledger row written, not committed, no gate
        row) completes the `idea` row instead of refusing the trial."""
        files = self._ready(card)
        rows, head = self.ledger.rows(), self.git.head()
        written = next((row for row in rows if row["trial_id"] == card.trial_id), None)
        if written is not None and self._stopped_half_done(card, written):
            self.gates.append(self._idea_row(card.trial_id, written["registered_on"], head, ""))
            return files
        self._require_next(card, rows)
        append_idea = self.gates.prepare(self._idea_row(card.trial_id, today.isoformat(), head, ""))
        self.ledger.register(card.trial_id, card.experiment, card.description, IDEA_KIND, card.hypothesis,
                             protocol_path=card.path, today=today)  # fmt: skip
        append_idea()
        return files

    def _stopped_half_done(self, card: IdeaCard, row: dict) -> bool:
        """This card's own ledger row, uncommitted (a register that stopped before its gate row). A committed row with
        no gate row is a hand registration: `factory backfill` dates it by its commit."""
        if row["protocol_path"] != card.path:
            return False
        self._require_same(card, row)
        if row["kind"] != IDEA_KIND:
            raise RegistrationError(f"trial {card.trial_id}'s ledger row is kind {row['kind']!r}, not a factory idea")
        if self.git.first_commit_containing(f"\n{card.trial_id},", LEDGER_FILE) is not None:
            raise RegistrationError(f"trial {card.trial_id}'s ledger row is committed without its gate row: run "
                                    "`factory backfill`")  # fmt: skip
        return True

    def _require_next(self, card: IdeaCard, rows: list[dict]) -> None:
        if any(row["trial_id"] == card.trial_id for row in rows):
            raise RegistrationError(f"trial {card.trial_id} is already in {LEDGER_FILE}")
        if any(row["protocol_path"] == card.path for row in rows):
            raise RegistrationError(f"{card.path} is already registered (a variant is a new card with a new id)")
        expected = self._next_claimed(card, rows)
        if card.trial_id != expected:
            raise RegistrationError(
                f"{card.path}: field 'trial' is {card.trial_id}, the next ledger trial is {expected}"
            )

    def _next_claimed(self, card: IdeaCard, rows: list[dict]) -> str:
        """The lowest free id of the block claimed for the card's experiment (story O12e): no skipped id can hide a
        trial, and no branch takes another's ids ("highest plus one" did both on parallel branches)."""
        try:
            return self.ledger.claims.next_free(card.experiment, {row["trial_id"] for row in rows})
        except ValueError as unclaimed:
            raise RegistrationError(f"{card.path}: {unclaimed}") from unclaimed

    def backfill(self, card: IdeaCard) -> tuple[str, ...]:
        """The `idea` row of a card whose ledger row was written by hand before R1's code."""
        files = self._ready(card)
        row = next((r for r in self.ledger.rows() if r["trial_id"] == card.trial_id), None)
        if row is None:
            raise RegistrationError(f"{card.path}: trial {card.trial_id} is not in {LEDGER_FILE}; register it")
        self._require_same(card, row)
        commit = self.git.first_commit_containing(f"\n{card.trial_id},", LEDGER_FILE)
        if commit is None:
            raise RegistrationError(f"trial {card.trial_id}: its ledger row is not committed")
        self.gates.append(self._idea_row(card.trial_id, row["registered_on"], commit, BACKFILLED))
        return files

    def _ready(self, card: IdeaCard) -> tuple[str, ...]:
        """The files to commit; refuses before writing when other files are staged or the trial has a gate row."""
        files = (card.path, LEDGER_FILE, GATES_FILE)
        others = sorted(set(self.git.staged_paths()) - set(files))
        if others:
            raise RegistrationError(f"other files are staged ({', '.join(others)}): commit the registration alone")
        self.gates.require_append_only()
        if self.gates.last(card.trial_id) is not None:
            raise RegistrationError(f"trial {card.trial_id} already has a gate-log row")
        return files

    @staticmethod
    def _require_same(card: IdeaCard, row: dict) -> None:
        for field, card_value in (("experiment", card.experiment), ("description", card.description),
                                  ("hypothesis", "yes" if card.hypothesis else "no")):  # fmt: skip
            if row[field] != card_value:
                raise RegistrationError(f"{card.path}: field {field!r} differs from trial {card.trial_id}'s ledger row")

    @staticmethod
    def _idea_row(trial_id: str, on: str, commit: str, numbers: str) -> GateRow:
        return GateRow(trial_id, Gate.IDEA_CARD, Outcome.IDEA, on, commit, numbers)
