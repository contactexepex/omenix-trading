"""Composition root of the recommender's evening check (story REC1c): the repository's receipts folder, the verified
Drive reader of the data area, NSE's trading sessions, the school dashcam's sealed outcomes, the write-once store with
pushed receipts (shared with the daily record) and the #fno-desk alert sender. Apart from `wiring.py` so each root
wires one command."""

from __future__ import annotations

import os

from ..models import now_utc
from ..storage.data_wiring import DATA_AREA, RECEIPTS_FOLDER, REPOSITORY, build_data_store, build_drive_cache
from .check_run import CheckPorts, CheckRun
from .outcomes import SealedOutcomes
from .wiring import WRITER, build_receipt_publisher, trading_sessions
from .write_once import WriteOnce


def build_check_run(env=os.environ) -> CheckRun:
    from ..composition import build_alert_sender
    from ..school.dashcam.reader import VerifiedDriveReader
    from ..school.dashcam.wiring import build_dashcam

    sessions = trading_sessions()
    reader = VerifiedDriveReader(build_drive_cache(env), DATA_AREA)
    ports = CheckPorts(REPOSITORY / RECEIPTS_FOLDER / DATA_AREA, reader.read, sessions,
                       lambda: SealedOutcomes(build_dashcam(env=env), sessions))  # fmt: skip
    keeper = WriteOnce(build_data_store(WRITER, None, env), build_receipt_publisher())
    return CheckRun(ports, keeper, build_alert_sender(), now_utc)
