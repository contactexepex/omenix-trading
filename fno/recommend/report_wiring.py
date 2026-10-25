"""Composition root of the recommender's edition block (story REC1d): its switch (`daily.live_from.recommend`, the
recommender's own key; never `school.reports`), the receipts shelf, the verified Drive reader of the data area,
NSE's trading sessions for the previous session, and the run log's `recommend` step for the evening's no-record
line. With no live date the lab's maker is returned as it was given."""

from __future__ import annotations

import functools
import re
from datetime import date, timedelta
from pathlib import Path

from ..config import ROOT, load_app_config
from .constants import RECOMMEND_STEP
from .report_maker import RecommendReportMaker
from .report_section import EveningSection, MorningSection, ReportPorts

MORNING, EVENING = "morning", "evening"
WORD, CODE = re.compile(r"[a-z_]+"), re.compile(r"[a-z0-9_]+:[A-Z0-9_]+")  # O1's statuses and reason codes
UNKNOWN = "unknown"  # an older log's free-text reason is never shown
LOOK_BACK_DAYS = 15  # longer than any NSE closure, so the previous session is always inside it


def live_from(config: dict) -> date | None:
    raw = (config.get("daily", {}).get("live_from", {}) or {}).get(RECOMMEND_STEP)
    return date.fromisoformat(str(raw)) if raw else None


def build_recommend_maker(maker, config: dict | None = None, ports: ReportPorts | None = None):
    first = live_from(config if config is not None else load_app_config())
    if first is None:
        return maker
    ports = ports or build_report_ports()
    return RecommendReportMaker(maker, {MORNING: MorningSection(ports), EVENING: EveningSection(ports)}, first)


def build_report_ports() -> ReportPorts:
    from ..school.dashcam.reader import VerifiedDriveReader
    from ..storage.data_wiring import DATA_AREA, RECEIPTS_FOLDER, REPOSITORY, build_drive_cache
    from .shelf import ReceiptShelf
    from .wiring import trading_sessions

    sessions = trading_sessions()

    def previous_session(day: date) -> date | None:
        before = sessions(day - timedelta(days=LOOK_BACK_DAYS), day - timedelta(days=1))
        return before[-1] if before else None

    reader = VerifiedDriveReader(build_drive_cache(), DATA_AREA)
    return ReportPorts(ReceiptShelf(REPOSITORY / RECEIPTS_FOLDER / DATA_AREA), reader.read, previous_session,
                       functools.partial(recommend_step, ROOT))  # fmt: skip


def recommend_step(root: Path, day: date) -> tuple[str, str] | None:
    """The run log's `recommend` status and reason code: never the step's printed lines (judge 664 m1)."""
    from ..desk.run_log import RunLog

    found = RunLog.open(root, day).steps.get(RECOMMEND_STEP)
    if found is None:
        return None
    status, reason = found["result"]["status"], found["result"]["reason"]
    return (status if WORD.fullmatch(status) else UNKNOWN), (reason if CODE.fullmatch(reason) else UNKNOWN)
