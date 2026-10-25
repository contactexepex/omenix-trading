"""When an ordered exit is filled (stories E4 and E8): E4 closes at the execution snapshot that ordered it; E8's
owner-timing views only alert the owner and leave the close to the owner-timing fill at the next session's due mark.
A strategy behind one interface, so the exit review itself (settlement, protection, the exit rules) stays E4's."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from .records import DeskJournal
from .snapshot import ExecutionSnapshot
from .status import OpenPosition

if TYPE_CHECKING:
    from .exits import ExitResult


class ExitTiming(ABC):
    @abstractmethod
    def defer(self, book: str, position: OpenPosition, snapshot: ExecutionSnapshot,
              journal: DeskJournal) -> ExitResult | None:  # fmt: skip
        """What happened instead of closing now (the exit is ordered and stays open), or None to close now."""


class ImmediateExits(ExitTiming):
    """E4's rule: an ordered exit closes at this snapshot's valid quotes."""

    def defer(self, book, position, snapshot, journal) -> ExitResult | None:
        return None
