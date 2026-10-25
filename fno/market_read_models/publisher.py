"""Where a session's blocks are published (story P6): behind one interface, all blocks or none. A failed publish
leaves the previous publication current and unchanged; publishing the same publication again changes nothing (a
publication is named by its content, so the same session's same pages always have the same ID)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .publication import Publication


class PublishFailed(RuntimeError):
    """Nothing of the publication became visible; the previous one is still current. `failure_class` names a database
    failure (db_errors), None for any other refusal."""

    def __init__(self, message: str, failure_class: str | None = None):
        super().__init__(message)
        self.failure_class = failure_class


class ReadModelPublisher(ABC):
    name: str = "publisher"

    @abstractmethod
    def publish(self, publication: Publication) -> int:
        """Makes every record of the publication current at once (PublishFailed: none of them); the number of pages
        it added (0: published before)."""

    @abstractmethod
    def stored(self, publication_id: str) -> dict[str, str]:
        """Page key -> payload SHA-256 of what the store holds for the publication, read back from the store."""

    @abstractmethod
    def current(self) -> dict[str, dict]:
        """The current publication's records by page key (empty before the first publication)."""
