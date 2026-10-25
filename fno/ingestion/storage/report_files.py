"""A report rewritten every run (O9b): written through one port, so where it lives is the composition root's choice.
`ReceiptedSnapshots` (`receipted_rows.py`) keeps one write-once Drive file per run with its receipt."""

from __future__ import annotations

from abc import ABC, abstractmethod


class Report(ABC):
    @abstractmethod
    def write(self, fields: tuple[str, ...], rows: list[tuple]) -> None:
        """The report's whole new content."""
