"""Report sections (story MS-P1g) and the banner: red or amber only, by design (327 item 9). No green exists."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Protocol, runtime_checkable


class Banner(StrEnum):
    RED = "red"  # do not trade real money today
    AMBER = "amber"  # paper only


@dataclass(frozen=True)
class SectionText:
    title: str
    lines: tuple[str, ...]
    banner: Banner


@runtime_checkable
class ReportSection(Protocol):
    def render(self, session: date) -> SectionText: ...
