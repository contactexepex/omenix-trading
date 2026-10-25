"""The components of a book's active D6 version on a day (story D4): the latest row of `journal/versions.csv` for the
book that starts on or before the day. C4 compares the trade envelope's file hash with it. Whether that row was
registered in time is D6's own check when the decision is scored."""

from __future__ import annotations

from datetime import date

from .version_registry import VersionRegistry


class RegisteredComponents:
    def __init__(self, registry: VersionRegistry):
        self.registry = registry

    def __call__(self, book: str, day: date) -> dict[str, str]:
        rows = [r for r in self.registry.rows() if r.book == book and r.starts_on <= day]
        return dict(max(rows, key=lambda r: r.starts_on).components) if rows else {}
