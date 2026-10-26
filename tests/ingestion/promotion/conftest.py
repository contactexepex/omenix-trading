"""Fakes for the staging -> promotion tests: folders under tmp_path stand in for Drive; a source that serves bytes
from a dict stands in for NSE. Nothing here touches the network."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from fno.ingestion.promotion.gate import RevisionSink
from fno.ingestion.research_data.calendar import load_session_calendar
from fno.ingestion.storage.raw_source import ParticipantOiSource, RawFileRefused
from fno.ingestion.storage.raw_store import LocalFolderStore, RawFileStore

FIXTURE_CALENDAR = Path(__file__).parents[2] / "fixtures" / "nse_sessions_2026.csv"
GOOD = b"good,bytes\n"
WEDNESDAY, THURSDAY, FRIDAY, SATURDAY = date(2026, 10, 21), date(2026, 10, 22), date(2026, 10, 23), date(2026, 10, 24)


def moment(day: date, hour: int = 12) -> datetime:
    return datetime(day.year, day.month, day.day, hour, 0, 0, tzinfo=UTC)


class SpyStore(RawFileStore):
    """Wraps a store and remembers every path it was asked to save."""

    def __init__(self, store: RawFileStore):
        self.store, self.saved = store, []
        self.name = store.name

    def get(self, path):
        return self.store.get(path)

    def put(self, path, data):
        self.saved.append(path)
        self.store.put(path, data)

    def folders(self, folder):
        return self.store.folders(folder)


class RecordingSink(RevisionSink):
    """Remembers the later versions the gate offered; `new` says which bytes count as new (default: all)."""

    def __init__(self):
        self.offered: list[tuple[str, bytes, datetime]] = []

    def capture(self, path, data, found_at):
        if any(d == data for _, d, _ in self.offered):
            return False
        self.offered.append((path, data, found_at))
        return True


class FakeNse(ParticipantOiSource):
    """Serves the bytes in `files` by archive path; a path in `refused` raises the source's per-file refusal."""

    def __init__(self, files: dict[str, bytes] | None = None, refused: set[str] | None = None):
        self.files, self.refused = files or {}, refused or set()

    def fetch(self, path):
        if path in self.refused:
            raise RawFileRefused("HTTP 403")
        return self.files.get(path)


@pytest.fixture
def calendar():
    return load_session_calendar(FIXTURE_CALENDAR)


@pytest.fixture
def sink():
    return RecordingSink()


@pytest.fixture
def staging_store(tmp_path):
    return SpyStore(LocalFolderStore(tmp_path / "staging"))


@pytest.fixture
def record_store(tmp_path):
    return SpyStore(LocalFolderStore(tmp_path / "record"))
