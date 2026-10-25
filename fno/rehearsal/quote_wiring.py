"""A4's recorders in a rehearsal (story REH1b), chosen where each is built: unchanged in a real run, the recorded
recorder when rehearsing. Its record is a read-only quote store of the same kind as the live one: the record
checkout's sidecars and markers, and for Groww the real Drive's quote files, each verified against its sidecar's
SHA-256 as A4b reads them."""

from __future__ import annotations

import os
from collections.abc import Mapping

from .mode import Rehearsal, rehearsal


def rehearsed_recorder(recorder, env: Mapping[str, str] = os.environ):
    mode = rehearsal(env)
    if mode is None:
        return recorder
    from .recorded_quotes import RecordedRecorder

    return RecordedRecorder(recorder, record_quote_store(recorder.store, mode))


def record_quote_store(store, mode: Rehearsal):
    from ..config import ROOT
    from ..quotes.drive_only_store import DriveOnlyQuoteStore
    from ..storage.raw_store import AreaStore, LocalFolderStore
    from ..storage.wiring import QUOTES_FOLDER, RAW_AREA, build_owner_drive
    from .record_store import ListedQuoteRecord, RecordReader

    repository = RecordReader(LocalFolderStore(mode.record / QUOTES_FOLDER.relative_to(ROOT)))
    if not isinstance(store, DriveOnlyQuoteStore):
        return repository

    def private():
        drive = build_owner_drive()
        return AreaStore(drive.record_view(), RAW_AREA) if drive is not None else None

    return ListedQuoteRecord(repository, private, store.prefix.rstrip("/"), store.unavailable)
