"""The global cues' session in a rehearsal (story REH1c), chosen by `fno/global_cues/wiring.py`: the live publishers
in a real run, the day's archived copies when rehearsing."""

from __future__ import annotations

import os
import time
from collections.abc import Mapping

from .mode import rehearsal


def rehearsed_cue_session(session, env: Mapping[str, str] = os.environ):
    mode = rehearsal(env)
    if mode is None:
        return session
    from ..config import ROOT
    from ..models import now_ist
    from ..storage.wiring import MANIFEST_FOLDER, RAW_AREA
    from .record_drive import RecordFiles
    from .recorded_cues import RecordedCueSession

    logs = mode.record / MANIFEST_FOLDER.relative_to(ROOT) / "global-cues"
    return RecordedCueSession(logs, RecordFiles(RAW_AREA), now_ist, time.sleep)
