"""The counting rule (story MS-P1h, D6's rule): a decision counts only if, strictly before the decision's own commit,
the first counted session was set, the comparison card was frozen and the driver's version row was registered; the
driver's card is the one its row names; the row names the comparison card version in force; and the session is on or
after the first counted session. Each decision is
judged against the card version and the first counted session in force at its own commit, so a later change applies
only to later decisions and never re-counts or un-counts an earlier one. Anything else is kept in the denominator."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Protocol

from ..constants import RoadCode

CARD_PATH = "research/school/CARD_P1.md"
CONFIG_PATH = "config.yaml"


class NotCounted(StrEnum):
    NO_FIRST_COUNTED_SESSION = "no_first_counted_session"
    FIRST_COUNTED_NOT_FROZEN_BEFORE = "first_counted_not_frozen_before"
    BEFORE_FIRST_COUNTED_SESSION = "before_first_counted_session"
    CARD_NOT_FROZEN_BEFORE = "card_not_frozen_before"
    COMPARISON_CARD_MISMATCH = "comparison_card_mismatch"
    VERSION_NOT_REGISTERED_BEFORE = "version_not_registered_before"
    DRIVER_CARD_CHANGED = "driver_card_changed"


@dataclass(frozen=True)
class CountCandidate:
    """What a sealed decision gives the rule: its place, the driver card it ran on and the commit that holds it."""

    session: date
    road: RoadCode
    driver_id: str  # e.g. "CS1@1"
    card_sha256: str
    commit: str


@dataclass(frozen=True)
class CountVerdict:
    counted: bool
    reason: NotCounted | None = None
    card_commit: str | None = None  # the comparison card version it counted under: results group by it


@dataclass(frozen=True)
class FirstCounted:
    """The value of `school.first_counted` in a commit's tree, and the commit that first wrote that value."""

    day: date | None
    set_in: str | None


@dataclass(frozen=True)
class RegisteredVersion:
    """What a driver version's D6 row names: its driver card and the comparison card it was registered under."""

    card_sha256: str | None
    comparison_card_sha256: str | None


class CountingHistory(Protocol):
    def is_ancestor(self, older: str, newer: str) -> bool: ...

    def card_commits(self) -> list[str]:
        """Every commit that changed the comparison card, oldest first."""

    def first_counted_at(self, commit: str) -> FirstCounted:
        """`school.first_counted` as committed at `commit`."""

    def card_sha256_at(self, commit: str) -> str:
        """The SHA-256 of the comparison card as committed at `commit`."""


class VersionLookup(Protocol):
    def registered_before(self, driver_id: str, session: date, decision_commit: str) -> RegisteredVersion | None:
        """The driver's active version whose row and components were committed strictly before the decision's commit
        (D6's ancestry rule), or None when there is none."""


class CountingRule:
    def __init__(self, history: CountingHistory, versions: VersionLookup):
        self.history, self.versions = history, versions

    def verdict(self, candidate: CountCandidate) -> CountVerdict:
        first = self.history.first_counted_at(candidate.commit)
        if first.day is None:
            return CountVerdict(False, NotCounted.NO_FIRST_COUNTED_SESSION)
        if not self._strictly_before(first.set_in, candidate.commit):
            return CountVerdict(False, NotCounted.FIRST_COUNTED_NOT_FROZEN_BEFORE)
        if candidate.session < first.day:
            return CountVerdict(False, NotCounted.BEFORE_FIRST_COUNTED_SESSION)
        card = self._card_in_force(candidate.commit)
        if card is None:
            return CountVerdict(False, NotCounted.CARD_NOT_FROZEN_BEFORE)
        registered = self.versions.registered_before(candidate.driver_id, candidate.session, candidate.commit)
        if registered is None:
            return CountVerdict(False, NotCounted.VERSION_NOT_REGISTERED_BEFORE, card)
        if registered.card_sha256 != candidate.card_sha256:
            return CountVerdict(False, NotCounted.DRIVER_CARD_CHANGED, card)
        if registered.comparison_card_sha256 != self.history.card_sha256_at(card):
            return CountVerdict(False, NotCounted.COMPARISON_CARD_MISMATCH, card)
        return CountVerdict(True, card_commit=card)

    def _card_in_force(self, decision_commit: str) -> str | None:
        """The card's last change strictly before the decision: later versions apply only to later decisions."""
        frozen = [c for c in self.history.card_commits() if self._strictly_before(c, decision_commit)]
        return frozen[-1] if frozen else None

    def _strictly_before(self, commit: str | None, decision_commit: str) -> bool:
        """An ancestor of, and not, the decision's own commit (a change in the decision's commit does not count it)."""
        return commit is not None and commit != decision_commit and self.history.is_ancestor(commit, decision_commit)
