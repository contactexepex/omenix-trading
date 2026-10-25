"""Reads a dataset only through its record (story DR1): the bytes the record names, verified against its SHA-256, and
the as-seen pointer the decision keeps. A certified record serves a provisional need; a provisional one never serves a
certified need. No record, or bytes that do not match, is refused with a named reason; nothing lists Drive or picks
among copies, so a stray staged file can never make a dataset unreadable."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from ..storage.raw_store import RawFileStore
from .constants import CERTIFIED, LEVELS, NOT_READABLE, NOT_RECORDED, PROVISIONAL
from .models import AsSeen
from .record_folder import RecordFolder


class NotRecorded(LookupError):
    """No record serves the need, or its bytes are missing or other; the message names which (never a value)."""


@dataclass(frozen=True)
class Seen:
    data: bytes
    as_seen: AsSeen


class RecordReader:
    def __init__(self, records: RecordFolder, drive: RawFileStore):
        self.records, self.drive = records, drive

    def read(self, dataset: str, session: str, need: str) -> Seen:
        if need not in LEVELS:
            raise ValueError(f"level {need!r} is not one of {LEVELS}")
        for level in (CERTIFIED, PROVISIONAL) if need == PROVISIONAL else (CERTIFIED,):
            chosen = self.records.chosen(dataset, session, level)
            if chosen is None:
                continue
            data = self.drive.get(chosen.path)
            if data is None or hashlib.sha256(data).hexdigest() != chosen.sha256:
                why = "missing from Drive" if data is None else "other bytes than recorded"
                raise NotRecorded(NOT_READABLE.format(dataset=dataset, session=session, level=level, why=why))
            return Seen(data, AsSeen(dataset, session, level, chosen.path, chosen.sha256))
        raise NotRecorded(NOT_RECORDED.format(dataset=dataset, session=session, level=need))
