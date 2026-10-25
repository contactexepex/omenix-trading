"""NSE's archive in a rehearsal, chosen by `build_nse_source`: the session never sends a request. REH1b's
`NotRecordedSession` fails every request at once as one that could never be sent, so the library's own rule applies
(no retry, no wait, nothing archived) and the step's line says why. REH1h's `RecordedArchiveSession`, the session a
rehearsal gets, extends it: a file the day's own routine archived is served from the record near its row's commit
(`recorded_archive`); every other request is still "not recorded". A file Drive already holds is read from Drive as in
a real run."""

from __future__ import annotations

import os
import time
from collections.abc import Mapping

import requests

from .mode import rehearsal

NOT_RECORDED = "rehearsal:NOT_RECORDED {url}: not in the record, and a rehearsal never fetches"


class NotRecorded(requests.exceptions.InvalidURL):
    """A rehearsal's request to a live source: never sent (the record did not hold the file)."""


class NotRecordedSession:
    def __init__(self):
        self.headers: dict[str, str] = {}

    def get(self, url, *args, **kwargs):
        raise NotRecorded(NOT_RECORDED.format(url=url))

    def head(self, url, *args, **kwargs):
        raise NotRecorded(NOT_RECORDED.format(url=url))


def rehearsed_session(session, env: Mapping[str, str] = os.environ):
    mode = rehearsal(env)
    if mode is None:
        return session
    from ..models import now_ist
    from ..storage.wiring import RAW_AREA
    from .manifest_rows import ManifestRows
    from .record_drive import RecordFiles
    from .recorded_archive import RecordedArchiveSession

    return RecordedArchiveSession(ManifestRows(mode.record), mode.day, RecordFiles(RAW_AREA), now_ist, time.sleep)
