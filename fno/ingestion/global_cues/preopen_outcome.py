"""What one index's pre-open read gave (story A17f): its lines, its status and its problems, each problem with the O10
kind it is recorded under. A problem's text names the index, a status or an error class and the reason; never a level
(private, owner rule 50a79a43), and it is what the #fno-desk alert and O10's row carry, not stdout only."""

from __future__ import annotations

from dataclasses import dataclass

FAILURE, INCOMPLETE = "failure", "incomplete"  # O10 kinds: a read or rule that failed; data that did not come


@dataclass(frozen=True)
class Problem:
    text: str
    kind: str = FAILURE


@dataclass(frozen=True)
class ReadOutcome:
    lines: tuple[str, ...]
    status: str
    problems: tuple[Problem, ...] = ()
