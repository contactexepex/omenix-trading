"""Composition root of the forecast lab's two report editions (stories FL1-1 and FL1-1d): G13b's reader and closes
(synced verified from Drive into O9's cache first, its back-fill too for the page's history), FL1's adapter, the
message's content (`page_wiring.py`), O9's data store for each edition's records, the Slack file poster pointed at
#fno-forecast, the alert sender for #fno-desk, the A7 calendar and the IST clock. Each edition is live from its own
`forecast_lab.live_from` date in config.yaml; in a rehearsal of a day before it, the edition runs and every post says
it is not live in real runs (story REH1k)."""

from __future__ import annotations

import os
from datetime import date

from ..composition import build_alert_sender, build_session_calendar
from ..config import ROOT, load_app_config
from ..constants import ENV_FNO_SLACK_BOT_TOKEN, FNO_FORECAST_CHANNEL_ID
from ..models import now_ist
from ..storage.data_wiring import DATA_AREA, RECEIPTS_FOLDER, build_data_store, build_drive_cache, receipt_folder
from .composers import EveningComposer, MorningComposer
from .confirm import Confirmation
from .constants import EVENING, MORNING, MORNING_BY, REPORT_AREAS
from .delivery import NoReportPoster, ReportPoster, SlackFilesPoster
from .edition_run import Composer, Edition, EditionRun
from .g13b_adapter import G13bCloses, G13bRanges
from .match import MatchSection
from .official_closes import ArchivedCloses
from .page_wiring import build_report_maker
from .preview import Preview
from .records import DriveReportRecords
from .release import FlowsRelease, ReleaseChecks
from .report import CloseReport
from .sessions import RegularSessions

WRITER = "forecast-lab"
RELEASE_FOLDER, RELEASE_LOG = ROOT / "research" / "data" / "forecast_lab" / "release", "release_checks.csv"
UNSYNCED = "G13b's records could not be read verified from Drive: {problems}"


def receipt_pathspecs(edition: str) -> tuple[str, ...]:
    """The receipts of one edition's own Drive files only (its routine commits these), never a shared folder."""
    return (f"{RECEIPTS_FOLDER}/{DATA_AREA}/{REPORT_AREAS[edition]}/",)


def build_forecast_poster(env=os.environ) -> ReportPoster:
    """#fno-forecast with `FNO_SLACK_BOT_TOKEN` only; without it nothing is sent and the outcome says so."""
    token = env.get(ENV_FNO_SLACK_BOT_TOKEN)
    from ..rehearsal.report_label import rehearsed_report_poster

    return rehearsed_report_poster(SlackFilesPoster(token, FNO_FORECAST_CHANNEL_ID) if token else NoReportPoster())


def live_from(cfg: dict) -> dict[str, date | None]:
    """`forecast_lab.live_from`: each edition's first live day; an edition without one is not live."""
    raw = (cfg.get("forecast_lab") or {}).get("live_from") or {}
    return {e: date.fromisoformat(str(raw[e])) if raw.get(e) else None for e in (MORNING, EVENING)}


def lab_live(cfg: dict, env=os.environ) -> tuple[dict[str, date | None], dict[str, str]]:
    """Each edition's live date for this run, and the note of each edition made live only by a rehearsal (REH1k)."""
    from ..rehearsal.live_wiring import rehearsed_live

    return rehearsed_live(live_from(cfg), env)


def g13b_issues_from(cfg: dict) -> date | None:
    """G13b's first live day: no forecast is expected from an issue day before it."""
    from ..daily.wiring import live_dates

    return live_dates(cfg)["price_ranges"]


def records(edition: str, env=os.environ) -> DriveReportRecords:
    return DriveReportRecords(build_data_store(WRITER, env=env), receipt_folder(), REPORT_AREAS[edition])


def build_release_checks() -> ReleaseChecks:
    """The evening's read-only release check: the F&O bhavcopy through A8's recorder, FII and DII cash by session."""
    from ..composition import build_session_calendar as calendar
    from ..research_data.release_times import ReleaseLog, ReleaseTimeRecorder
    from ..storage.raw_source import NseDailyFoSource
    from ..storage.snapshot_source import FiiDiiCashBySessionSource
    from ..storage.wiring import build_nse_source

    fo = ReleaseTimeRecorder(build_nse_source(NseDailyFoSource), NseDailyFoSource.path_for, calendar(),
                             ReleaseLog(RELEASE_FOLDER / "fo-bhavcopy" / RELEASE_LOG))  # fmt: skip
    flows = FlowsRelease(build_nse_source(FiiDiiCashBySessionSource), FiiDiiCashBySessionSource.path_for,
                         ReleaseLog(RELEASE_FOLDER / "fii-dii-cash" / RELEASE_LOG))  # fmt: skip
    return ReleaseChecks({"fo-bhavcopy": fo, "fii-dii-cash": flows})


def build_composer(edition: str, env=os.environ, live: dict[str, date | None] | None = None
                   ) -> tuple[Composer, RegularSessions, dict[str, date | None]]:  # fmt: skip
    """The edition's composer over the synced Drive cache (read-only: only `EditionRun` writes records), the regular
    sessions and each edition's live date (`live`: the edition's run passes its own, REH1k)."""
    from ..price_ranges import wiring as g13b
    from ..price_ranges.closes import IndexFileCloses, Outcomes
    from ..price_ranges.folders import BACKFILL, LIVE, SCORES, drive
    from ..price_ranges.reader import RangeForecasts, RangeScores
    from ..storage.wiring import build_stored_index_close_files

    cache = build_drive_cache(env)
    problems = [p for prefix in (drive(LIVE), drive(SCORES), drive(BACKFILL)) for p in cache.sync(prefix).problems]
    if problems:
        raise RuntimeError(UNSYNCED.format(problems="; ".join(problems)))
    store = g13b.build_store(env)
    forecasts, scores = RangeForecasts(g13b.CACHE_ROOT, g13b.build_seals(store)), RangeScores(g13b.CACHE_ROOT)
    ranges = G13bRanges(forecasts, scores)
    calendar, cfg = build_session_calendar(), load_app_config()
    closes = ArchivedCloses(G13bCloses(Outcomes(g13b.build_closes(g13b.build_tables(store)))),
                            IndexFileCloses(build_stored_index_close_files(), calendar))  # fmt: skip
    sessions, live = RegularSessions(calendar), lab_live(cfg, env)[0] if live is None else live
    maker = build_report_maker(ranges, forecasts, scores, calendar, closes)
    evenings, own = records(EVENING, env), records(edition, env)
    if edition == MORNING:
        return MorningComposer(maker, Confirmation(evenings.report, own.report, closes, sessions)), sessions, live
    report = CloseReport(ranges, MatchSection(ranges, closes, sessions, g13b_issues_from(cfg)), live[EVENING])
    return EveningComposer(report, maker, own.report), sessions, live


def build_edition(edition: str, env=os.environ) -> EditionRun:
    from ..rehearsal.live_wiring import note_this_process

    live, notes = lab_live(load_app_config(), env)
    note_this_process(notes.get(edition))  # REH1k: one edition per process
    composer, sessions, _ = build_composer(edition, env, live)
    cutoff = MORNING_BY if edition == MORNING else None
    return EditionRun(Edition(edition, live[edition], cutoff), composer, records(edition, env),
                      build_forecast_poster(env), build_alert_sender(), sessions.is_regular, now_ist)  # fmt: skip


def build_preview(edition: str, env=os.environ) -> Preview:
    """The owner's preview: the edition's composer, the #fno-forecast poster and its own records, read only."""
    composer, _, _ = build_composer(edition, env, live_from(load_app_config()))  # the real dates: no rehearsal note
    return Preview(composer, build_forecast_poster(env), records(edition, env).report)
