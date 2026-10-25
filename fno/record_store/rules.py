"""A dataset's certification rules (story DR1): the checks for each level and how one version is chosen among those
that pass. Choice by quality only (owner, 23 Oct 2026): a rule may refuse to choose, never pick by time."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

from .models import CheckResult, StagedVersion


class SourceUnreadable(RuntimeError):
    """A source the checks need could not be read at all (no store, a store refusing, a damaged file): the session is
    not recorded and the run fails loudly, never as an ordinary "not out yet" (orchestrator, 24 Oct 2026)."""


@dataclass(frozen=True)
class Choice:
    version: StagedVersion | None  # None: no record, `reason` says why
    reason: str


class DatasetRules(ABC):
    name: str
    version: str  # bumped whenever a check or the choice changes; kept in every record
    live_from: date  # the first session the dataset has versions for; a catch-up never asks for an earlier one

    @abstractmethod
    def checks(self, session: str, level: str, data: bytes) -> list[CheckResult]:
        """The level's checks of one version's bytes (integrity is checked before, by the certifier)."""

    @abstractmethod
    def choose(self, session: str, level: str, passing: list[tuple[StagedVersion, bytes]]) -> Choice:
        """One version among those that passed every check, or none with the reason."""
