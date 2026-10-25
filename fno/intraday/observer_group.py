"""Several observers behind A16's one mark observer port (LM1's position monitor, A21's announcements poll): each runs
in order, isolated from the others, and within its own hard time limit (set at its owner's wiring line), so a hung
member can never hold the mark's commit or the next mark for longer than that. A failure or a time-out is named by the
member's class only and never skips the next member. A timed-out member is left running: it may still finish after
the mark's commit, and its files then go up with the next mark's commit."""

from __future__ import annotations

import threading
from collections.abc import Sequence
from datetime import date, datetime

from .document import SnapshotDocument
from .observer import MarkObserver, MembersFailed

MAX_LIMIT_SECONDS = 300.0  # no member may hold a mark for more than 5 of its 15 minutes
TIMED_OUT = "{member} timed out"


class ObserverGroup(MarkObserver):
    def __init__(self, members: Sequence[tuple[MarkObserver, float]]):
        """`members`: (observer, its time limit in seconds), in the order they run."""
        for _, limit in members:
            if not 0 < limit <= MAX_LIMIT_SECONDS:
                raise ValueError(f"a member's time limit must be in (0, {MAX_LIMIT_SECONDS:.0f}] seconds: {limit}")
        self.members = tuple(members)

    def after_mark(self, day: date, mark: datetime, document: SnapshotDocument | None, status: str) -> None:
        args = (day, mark, document, status)
        failed = [name for member, limit in self.members if (name := self._run(member, limit, *args))]
        if failed:
            raise MembersFailed(failed)

    def _run(self, member: MarkObserver, limit: float, *args) -> str:
        """'' when the member finished in time; otherwise its class name (and "timed out" when it hung)."""
        errors: list[BaseException] = []

        def call() -> None:
            try:
                member.after_mark(*args)
            except Exception as exc:  # isolation: kept by class name only
                errors.append(exc)

        worker = threading.Thread(target=call, daemon=True)  # a hung member is left behind, never waited for
        worker.start()
        worker.join(limit)
        name = type(member).__name__
        if worker.is_alive():
            return TIMED_OUT.format(member=name)
        return f"{name}: {type(errors[0]).__name__}" if errors else ""
