"""One problem of a pre-open run (story A22): a line of its alert and one O10 capture-error row."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Problem:
    step: str
    kind: str
    message: str

    def line(self) -> str:
        return f"{self.step} {self.kind}: {self.message}" if self.message else f"{self.step} {self.kind}"
