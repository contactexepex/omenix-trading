"""Publishing a sealed answer (stories F1 and G5's protocol, shared with F1t's decisions and F2's role cards): the
commitment first, written once, then, from a given moment, the reveal (answer and salt) that must hash to it.
Book-, role- and kind-agnostic (a path, a transport, a clock); it says nothing itself, so each caller keeps its own
messages. Standard library only (it runs in a routine before any install)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from .seal import Commitment, reveal_text
from .transport import SubmissionTransport

ALREADY_SEALED = "{path} already exists: sealed once, never again"
DIFFERENT_REVEAL = "{path} already holds a different reveal (written once)"


class SealRefused(RuntimeError):
    """A step that must not run (a second seal, a different reveal); the message says why."""


class SealedPublisher:
    def __init__(self, transport: SubmissionTransport, clock: Callable[[], datetime], sleep: Callable[[float], None]):
        self.transport, self.clock, self.sleep = transport, clock, sleep

    def is_sealed(self, path: str) -> bool:
        """Asked before the salt is kept, so a second seal never replaces the first one's salt."""
        return self.transport.existing(path) is not None

    def commit(self, path: str, commitment: Commitment, message: str) -> str:
        """Publishes the commitment; the commit that holds it. The caller asked `is_sealed` first (one pull, as the
        forecast always did), before keeping its salt."""
        return self.transport.publish(path, commitment.to_text(), message)

    def wait_until(self, moment: datetime) -> None:
        wait = (moment - self.clock()).total_seconds()
        if wait > 0:
            self.sleep(wait)

    def reveal(self, path: str, answer: dict, salt: str, message: str) -> str | None:
        """Publishes the reveal once: its commit, or None when the same reveal is already published."""
        text, existing = reveal_text(answer, salt), self.transport.existing(path)
        if existing is not None:
            if existing != text:
                raise SealRefused(DIFFERENT_REVEAL.format(path=path))
            return None
        return self.transport.publish(path, text, message)
