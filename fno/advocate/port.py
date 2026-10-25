"""The objecting AI's port (story LR1; T3 reuses it with the daily card as its subject). A subject is a committed
file of code-built lines; the advocate returns checked objections to it, or says why it did not run. Its objections
are shown in their own labelled section: they never change a number and decide no trade."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

NOT_RUN = "advocate not run: {reason}"


@dataclass(frozen=True)
class AdvocateSubject:
    name: str  # e.g. "weekly post-mortem 2026-10-17"
    lines_path: Path  # the committed code-built lines
    lines_sha256: str


@dataclass(frozen=True)
class AdvocateResult:
    objections: tuple[str, ...] = ()
    not_run: str = ""  # the reason, when no checked objection is available

    @property
    def ran(self) -> bool:
        return not self.not_run

    def lines(self) -> list[str]:
        return list(self.objections) if self.ran else [NOT_RUN.format(reason=self.not_run)]


class Advocate(ABC):
    @abstractmethod
    def objections(self, subject: AdvocateSubject) -> AdvocateResult:
        """Never raises: a missing or refused answer is a `not_run` result."""
