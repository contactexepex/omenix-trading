"""The owner's availability calendar (story E8 rule 8; owner, 16 Oct 2026, `docs/DESK_DECISIONS.md:219`).

Away dates are private: one append-only Drive file, a first line `salt,<random hex>` (never committed) and then one row
`YYYY-MM-DD,away` or `YYYY-MM-DD,available` per change, a date's latest row winning. The public repository holds only
seals: the SHA-256 of the file's first n lines (trailing whitespace and CR removed, joined with LF) and n. An order
sent at T reads the last seal committed before T, so "away" can never be chosen after the prices are known. A sealed
line that changed refuses everything until the sealed version is restored from Drive's version history; nothing ever
re-seals over a mismatch. The salt keeps a calendar of a few dates from being guessed back from its hash."""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime

from ...storage.raw_store import RawFileStore

SALT_PREFIX = "salt,"
SALT_MIN_HEX = 32
AWAY, AVAILABLE = "away", "available"
REPAIR = (
    "the availability file's sealed lines changed (sealed {lines} lines): restore the last sealed version from Drive's "
    "version history, then append any change as a new row; nothing is re-sealed over a mismatch"
)
MISSING = "the availability file is missing from Drive although seals exist: restore it from Drive's version history"
BAD_SALT = "the availability file must start with a line 'salt,<at least 32 hex digits>'"
BAD_ROW = "availability file line {number}: expected 'YYYY-MM-DD,away' or 'YYYY-MM-DD,available'"


class AvailabilityRefused(ValueError):
    """The calendar cannot be trusted: its sealed part changed, it is gone, or it is malformed."""


@dataclass(frozen=True)
class Seal:
    lines: int
    sha256: str


def normalised_lines(data: bytes) -> list[str]:
    """The file's lines as hashed: trailing whitespace and CR removed, trailing empty lines dropped."""
    lines = [line.rstrip() for line in data.decode().splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    return lines


def prefix_sha256(lines: list[str], count: int) -> str:
    return hashlib.sha256("\n".join(lines[:count]).encode()).hexdigest()


def _checked(lines: list[str]) -> dict[date, str]:
    """Each date's latest status; refuses a missing salt line or a malformed row."""
    salt = lines[0][len(SALT_PREFIX) :] if lines and lines[0].startswith(SALT_PREFIX) else ""
    if len(salt) < SALT_MIN_HEX or any(c not in "0123456789abcdef" for c in salt.lower()):
        raise AvailabilityRefused(BAD_SALT)
    statuses: dict[date, str] = {}
    for number, line in enumerate(lines[1:], start=2):
        day, _, status = line.partition(",")
        if status not in (AWAY, AVAILABLE):
            raise AvailabilityRefused(BAD_ROW.format(number=number))
        try:
            statuses[date.fromisoformat(day)] = status
        except ValueError as exc:
            raise AvailabilityRefused(BAD_ROW.format(number=number)) from exc
    return statuses


class SealLog(ABC):
    """The committed seals, each with the time its commit reached `main`."""

    @abstractmethod
    def sealed_before(self, moment: datetime) -> Seal | None:
        """The last seal committed before `moment`, or None."""

    @abstractmethod
    def latest(self) -> Seal | None:
        """The newest seal, committed or about to be."""

    @abstractmethod
    def add(self, seal: Seal, sealed_at: datetime) -> None:
        """Appends a seal row (the daily run commits it)."""


class Availability(ABC):
    @abstractmethod
    def away(self, day: date, as_of: datetime) -> bool:
        """Whether the owner is away on `day`, by the calendar sealed before `as_of`."""


class AlwaysAvailable(Availability):
    def away(self, day: date, as_of: datetime) -> bool:
        return False


class SealedDriveAvailability(Availability):
    def __init__(self, store: RawFileStore, path: str, seals: SealLog):
        self.store, self.path, self.seals = store, path, seals

    def away(self, day: date, as_of: datetime) -> bool:
        seal = self.seals.sealed_before(as_of)
        if seal is None:
            return False  # nothing sealed yet: every session counts as available
        return _checked(self._sealed_lines(seal)).get(day) == AWAY

    def late_rows(self, as_of: datetime) -> int:
        """Rows appended after the seal used at `as_of`: reported as late away entries, never applied."""
        seal = self.seals.sealed_before(as_of)
        if seal is None and not self.store.get(self.path):
            return 0
        return max(0, len(self._lines()) - (seal.lines if seal else 1))

    def _sealed_lines(self, seal: Seal) -> list[str]:
        lines = self._lines()
        if prefix_sha256(lines, seal.lines) != seal.sha256 or len(lines) < seal.lines:
            raise AvailabilityRefused(REPAIR.format(lines=seal.lines))
        return lines[: seal.lines]

    def _lines(self) -> list[str]:
        data = self.store.get(self.path)
        if not data:
            raise AvailabilityRefused(MISSING)
        return normalised_lines(data)


class AvailabilitySealer:
    """Seals the file's current version at the start of the daily run, before that day's card (rule 8)."""

    def __init__(self, store: RawFileStore, path: str, seals: SealLog):
        self.store, self.path, self.seals = store, path, seals

    def seal(self, now: datetime) -> Seal | None:
        """The new seal, or None when the file is absent and nothing was sealed, or unchanged since the last seal."""
        data, last = self.store.get(self.path), self.seals.latest()
        if not data:
            if last is not None:
                raise AvailabilityRefused(MISSING)
            return None
        lines = normalised_lines(data)
        _checked(lines)
        if last is not None and (len(lines) < last.lines or prefix_sha256(lines, last.lines) != last.sha256):
            raise AvailabilityRefused(REPAIR.format(lines=last.lines))
        seal = Seal(len(lines), prefix_sha256(lines, len(lines)))
        if seal == last:
            return None
        self.seals.add(seal, now)
        return seal
