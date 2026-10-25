"""What the common market pack is built from (story E2): each input hands over its items, every one with its source
and availability time, and its provenance (files and hashes), so the pack can be rebuilt from committed inputs. No
input reads anything under a book's journal folder: the common pack holds market data only (design 13.5)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date

from .pack_items import PackItem


@dataclass(frozen=True)
class InputBatch:
    items: tuple[PackItem, ...]
    provenance: dict = field(default_factory=dict)


class CommonInput(ABC):
    name: str  # the provenance key

    @abstractmethod
    def collect(self, day: date) -> InputBatch:
        """Every item this source holds for the day, with its own availability time (the pack applies the cutoff)."""
