"""What each part of the card is made of, and the interfaces of the sources that make them (story T1). A source never
computes a trading number: it reads committed records and says, in plain lines, what they hold and what is missing."""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

from ..constants import CardStatus


@dataclass(frozen=True)
class UsedRecord:
    """A committed record the card shows, by path and the SHA-256 of its committed bytes (the card's footer)."""

    path: str
    sha256: str

    @classmethod
    def of(cls, path: str, data: bytes) -> UsedRecord:
        return cls(path, hashlib.sha256(data).hexdigest())


@dataclass(frozen=True)
class CardSection:
    title: str
    lines: tuple[str, ...]
    used: tuple[UsedRecord, ...] = ()
    missing: tuple[str, ...] = ()


@dataclass(frozen=True)
class CardWarning:
    """Story T1e: the card's warning, a headline (glyph and word) and its detail. Only the renderer decides where it
    goes, so the owner's choice of placement is a one-place change."""

    headline: str
    detail: str


@dataclass(frozen=True)
class StatusReading:
    status: CardStatus
    reason_code: str
    section: CardSection


class StatusSource(ABC):
    @abstractmethod
    def status(self, day: date) -> StatusReading:
        """The desk's status for the day with its reason code (v1: always NO TRADE)."""


WEATHER_BLOCKS = "No new trades while the weather reading is missing (owner rule)."  # owner "4 A", 15 Oct 2026


class WarningSource(ABC):
    @abstractmethod
    def warning(self, day: date) -> CardWarning | None:
        """Story T1e: the card's warning for the day (a failed or refused desk step), or None."""


class WeatherSource(ABC):
    @abstractmethod
    def weather(self, day: date) -> CardSection:
        """The market weather as scored by its model, or a plain line saying it is not scored."""


class ForecastSource(ABC):
    @abstractmethod
    def forecasts(self, day: date) -> CardSection:
        """The forecasts on record for the day, each with its scored track record where one exists."""
