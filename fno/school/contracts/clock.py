"""The school's clock: every time a record or fill carries comes from here, so a replay uses a fixed clock."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class Clock(Protocol):
    def now(self) -> datetime: ...


@dataclass(frozen=True)
class FixedClock:
    at: datetime

    def __post_init__(self):
        if self.at.tzinfo is None:
            raise ValueError("a clock gives time-zone aware times")

    def now(self) -> datetime:
        return self.at
