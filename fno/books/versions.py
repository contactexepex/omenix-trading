"""Evaluation segments (story D6, design 12.5-12.6, 13.5): which registered version each decision belongs to, and when
scoring is paused. A decision is scored in the segment of its book's active version: the latest registered for that
book that starts on or before the decision's day and whose registry row, and `registered_in_commit`, were committed
strictly before the decision (git ancestry, not the decision's own commit). A decision whose served components (the
model actually served, prompt versions, playbook hashes and so on) are not exactly the active version's, a missing
component included, is `unscored`, and so is every later decision of that book until a new version is registered.
Labels are computed from the registry and the decisions alone, in a fixed order, so the same inputs always give the
same segments (S2 and S3 group by them)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from .version_registry import VersionRow, render

UNSCORED = "unscored"
VERSIONS_FILE = "journal/versions.csv"


@dataclass(frozen=True)
class DecisionFacts:
    """What D3's decision record gives D6: the book, day, record ID, the commit holding the record and the components
    the decision actually used."""

    book: str
    day: date
    decision_id: str
    commit: str
    served: Mapping[str, str]


@dataclass(frozen=True)
class Segment:
    book: str
    version_id: str | None  # None when unscored
    reason: str

    @property
    def scored(self) -> bool:
        return self.version_id is not None

    @property
    def label(self) -> str:
        return f"{self.book}/{self.version_id}" if self.scored else UNSCORED


class GitHistory(Protocol):
    def first_commit_containing(self, text: str, path: str) -> str | None: ...

    def is_ancestor(self, older: str, newer: str) -> bool: ...


class Versions:
    def __init__(self, rows: Sequence[VersionRow], history: GitHistory):
        self.rows, self.history = tuple(rows), history
        self._row_commits = {_key(row): history.first_commit_containing(_line(row), VERSIONS_FILE) for row in self.rows}

    def active_version(self, book: str, day: date, decision_commit: str | None = None) -> VersionRow | None:
        """The book's version in force on `day`; with a decision commit, only versions registered before it."""
        found = [
            row for row in self.rows
            if row.book == book and row.starts_on <= day
            and (decision_commit is None or self._registered_before(row, decision_commit))
        ]  # fmt: skip
        return found[-1] if found else None

    def _registered_before(self, row: VersionRow, decision_commit: str) -> bool:
        """Strictly before (design 13.5): a row or components committed in the decision's own commit do not count."""
        row_commit = self._row_commits[_key(row)]
        return row_commit is not None and all(
            commit != decision_commit and self.history.is_ancestor(commit, decision_commit)
            for commit in (row_commit, row.registered_in_commit)
        )


class Segments:
    """Every decision's segment, computed once in (book, day, decision ID) order."""

    def __init__(self, versions: Versions, decisions: Sequence[DecisionFacts]):
        self.versions = versions
        self._pauses: list[tuple[str, str, date]] = []  # (book, version paused, first unscored day), in order
        ordered = sorted(decisions, key=lambda d: (d.book, d.day, d.decision_id))
        self._segments = {d.decision_id: self._label(d) for d in ordered}

    def segment_of(self, decision_id: str) -> Segment:
        return self._segments[decision_id]

    def scoring_paused(self, book: str, day: date) -> bool:
        """True when a mismatch on or before `day` paused the book and its active version on `day` is still the one
        that was paused (no new version registered since)."""
        active = self.versions.active_version(book, day)
        return any(b == book and since <= day and active and active.version_id == v for b, v, since in self._pauses)

    def _label(self, decision: DecisionFacts) -> Segment:
        active = self.versions.active_version(decision.book, decision.day, decision.commit)
        if active is None:
            return Segment(decision.book, None, "no version registered and committed before this decision")
        paused = [(v, since) for b, v, since in self._pauses if b == decision.book]
        if paused and paused[-1][0] == active.version_id:
            return Segment(decision.book, None, f"scoring paused since {paused[-1][1]}: no new version registered yet")
        keys = set(active.components) | set(decision.served)  # a component the decision does not report is a mismatch
        differing = sorted(k for k in keys if active.components.get(k) != decision.served.get(k))
        if differing:
            self._pauses.append((decision.book, active.version_id, decision.day))
            return Segment(decision.book, None, f"served components differ from {active.version_id}: {differing}")
        return Segment(decision.book, active.version_id, "matches the active version")


def _key(row: VersionRow) -> tuple[str, str]:
    return row.book, row.version_id


def _line(row: VersionRow) -> str:
    """The row exactly as the registry file holds it (what git's search looks for)."""
    return render([row]).split("\n", 1)[1].rstrip("\n")
