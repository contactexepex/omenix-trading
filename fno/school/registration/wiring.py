"""Composition root of `fno/school/registration/` (story MS-P1h): the repository's git history (the research engine's
`Git`, one adapter) and D6's version registry, wired into the counting rule.

A driver version is a D6 row of the book `school:<driver id>` (e.g. `school:CS1@1`; D6's `SCHOOL_BOOK_PREFIX`), its
component `CARD_COMPONENT` (`card_sha256`) the frozen driver card's SHA-256. The first counted session is read from
`config.yaml` as committed at each decision's own commit, so it can never be set or moved after the decisions it
would count."""

import hashlib
from datetime import date

import yaml

from ...books.version_registry import SCHOOL_BOOK_PREFIX
from ...books.versions import Versions
from ...research_engine.ledger import Git
from ..constants import SETTINGS_KEY
from .counting import CARD_PATH, CONFIG_PATH, CountingRule, FirstCounted, RegisteredVersion

CARD_COMPONENT = "card_sha256"
COMPARISON_COMPONENT = "comparison_card_sha256"  # the comparison card as of the version the row was registered under
FIRST_COUNTED_KEY = "first_counted"
UNREADABLE = "school.first_counted {value!r} is not a date (YYYY-MM-DD)"
NOT_FOUND = "school.first_counted {value} is in the tree of {commit} but no commit of the history wrote it"
SHALLOW = "this checkout is a shallow clone: run git fetch --unshallow before counting"


class FirstCountedError(RuntimeError):
    """The value of `school.first_counted` cannot be read or its writing commit cannot be found: counting stops by name
    rather than silently counting nothing."""


class GitCountingHistory:
    def __init__(self, git: Git):
        self.git = git
        self._values: dict[str, date | None] = {}
        self._found: dict[str, FirstCounted] = {}

    def is_ancestor(self, older: str, newer: str) -> bool:
        return self.git.is_ancestor(older, newer)

    def card_commits(self) -> list[str]:
        return self.git.commits_touching(CARD_PATH)

    def card_sha256_at(self, commit: str) -> str:
        text = self.git.committed_text(CARD_PATH, commit)
        return hashlib.sha256(text.encode("utf-8")).hexdigest() if text is not None else ""

    def first_counted_at(self, commit: str) -> FirstCounted:
        """The value in the commit's tree and the commit that began its current run: found by reading the parsed value
        at every commit of the history that touched `config.yaml`, so any spelling of the line (aligned, quoted,
        commented) is found. A value that is there but never found raises."""
        if commit not in self._found:
            self._found[commit] = self._first_counted(commit)
        return self._found[commit]

    def _first_counted(self, commit: str) -> FirstCounted:
        value = self._value_at(commit)
        if value is None:
            return FirstCounted(None, None)
        if self.git.is_shallow():
            raise FirstCountedError(SHALLOW)
        began = None
        for touched in self.git.commits_touching(CONFIG_PATH):
            if touched != commit and not self.git.is_ancestor(touched, commit):
                continue
            began = (began or touched) if self._value_at(touched) == value else None  # a run of the same value
        if began is None:
            raise FirstCountedError(NOT_FOUND.format(value=value, commit=commit))
        return FirstCounted(value, began)

    def _value_at(self, commit: str) -> date | None:
        if commit not in self._values:
            text = self.git.committed_text(CONFIG_PATH, commit)
            block = (yaml.safe_load(text) or {}).get(SETTINGS_KEY) if text else None
            self._values[commit] = _as_date(block.get(FIRST_COUNTED_KEY)) if isinstance(block, dict) else None
        return self._values[commit]


def _as_date(value) -> date | None:
    """A date, or an ISO date written as text (the `school` settings accept both); empty is no value."""
    if value is None or isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as unreadable:
        raise FirstCountedError(UNREADABLE.format(value=value)) from unreadable


class D6VersionLookup:
    def __init__(self, versions: Versions):
        self.versions = versions

    def registered_before(self, driver_id: str, session: date, decision_commit: str) -> RegisteredVersion | None:
        row = self.versions.active_version(f"{SCHOOL_BOOK_PREFIX}{driver_id}", session, decision_commit)
        if row is None:
            return None
        return RegisteredVersion(row.components.get(CARD_COMPONENT), row.components.get(COMPARISON_COMPONENT))


def build_counting_rule(git: Git, versions: Versions) -> CountingRule:
    return CountingRule(GitCountingHistory(git), D6VersionLookup(versions))
