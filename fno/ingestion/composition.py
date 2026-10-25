"""Composition root of the F&O ingestion app: the only place that picks concrete classes for the app's services (raw
data stores and sources are wired in `fno/storage/wiring.py`). Swapping a provider or store changes this file only."""

from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path

from fno.ingestion.providers import AUTO_PROVIDER, get_provider
from fno.ingestion.providers.base import Provider
from fno.ingestion.providers.nse_quotes import NseQuoteProvider
from fno.ingestion.providers.public import PublicData
from fno.ingestion.quotes.expiry_listing import NseDailyFileExpiries
from fno.ingestion.quotes.market_levels import NseLevelSource
from fno.ingestion.quotes.recorder import DATASET as GROWW_QUOTE_DATASET
from fno.ingestion.quotes.recorder import NSE_DATASET as NSE_QUOTE_DATASET
from fno.ingestion.quotes.recorder import QuoteSnapshotRecorder
from fno.ingestion.research_data.availability import AvailabilityRule, LastWriteBoundRule
from fno.ingestion.research_data.last_written import latest_writes, read_last_modified_table
from fno.ingestion.research_data.release_check_once import ReleaseCheckOnce
from fno.ingestion.research_data.release_times import (
    ReleaseLog,
    ReleaseTimeRecorder,
    choose_availability_rule,
    last_written_times,
)
from fno.ingestion.research_data.reread_log import RereadLog
from fno.ingestion.research_data.write_sweep import LastWriteSweep, read_sweeps
from fno.ingestion.storage.raw_source import ParticipantOiSource
from fno.ingestion.storage.revisions import RevisionArchive
from fno.ingestion.storage.wiring import (
    PARTICIPANT_OI_LAST_MODIFIED,
    PARTICIPANT_OI_RELEASE_LOG,
    PARTICIPANT_OI_REREADS,
    PARTICIPANT_OI_SWEEPS,
    build_nse_fo_library,
    build_nse_source,
    build_quote_store,
    build_revision_capturing_source,
    build_session_calendar,
)
from fno.shared.alerts.sender import AlertSender, NoAlertSender, SlackChannelAlerts
from fno.shared.constants import DESK_DECISION_TIME, ENV_FNO_SLACK_BOT_TOKEN, FNO_DESK_CHANNEL_ID


def build_quote_recorder(cfg: dict) -> QuoteSnapshotRecorder:
    """The 3 pm quote recorder (story A4): its own `quotes.provider` setting (`auto`: Groww when its credentials are
    set, else NSE), never the root `provider` used by the `chain` command; the repository quote store; NSE's daily
    files, for expiry dates the provider cannot list and to prove which expiries are monthly (A5's point-in-time rule);
    NSE's session calendar, which decides whether today is a session (A7); and India VIX with the NIFTY futures from
    NSE's public website at capture, for the live features (B7)."""
    provider = get_provider(cfg.get("quotes", {}).get("provider", AUTO_PROVIDER), cfg)
    return _quote_recorder(provider, GROWW_QUOTE_DATASET)


def build_nse_quote_recorder(cfg: dict) -> QuoteSnapshotRecorder:
    """Story O6, owner's choice (a): the same recorder on NSE's public option chain (no broker key), into its own
    dataset beside Groww's, so the two can be compared and are never mixed."""
    return _quote_recorder(NseQuoteProvider(cfg), NSE_QUOTE_DATASET)


def _quote_recorder(provider: Provider, dataset: str) -> QuoteSnapshotRecorder:
    expiries, levels = NseDailyFileExpiries(build_nse_fo_library()), NseLevelSource(PublicData().nse_json)
    return QuoteSnapshotRecorder(
        provider,
        build_quote_store(),
        fallback=expiries,
        calendar=build_session_calendar(),
        history=expiries,
        levels=levels,
        dataset=dataset,
    )


def build_alert_sender() -> AlertSender:
    """Alerts go to #fno-desk with `FNO_SLACK_BOT_TOKEN`; without it, nothing is sent and the outcome says so."""
    token = os.environ.get(ENV_FNO_SLACK_BOT_TOKEN)
    return SlackChannelAlerts(token, FNO_DESK_CHANNEL_ID) if token else NoAlertSender()


def build_release_time_recorder(log: Path | None = None) -> ReleaseTimeRecorder:
    """Story A8: checks NSE's archive itself (never Drive) for a session's participant-OI file and logs each check
    (to `log`: story O6's side-by-side Actions run keeps its own)."""
    return ReleaseTimeRecorder(
        build_nse_source(ParticipantOiSource),
        ParticipantOiSource.path_for,
        build_session_calendar(),
        ReleaseLog(log or PARTICIPANT_OI_RELEASE_LOG),
    )


def build_release_check_once() -> ReleaseCheckOnce:
    """Story A8 on GitHub Actions: one check per scheduled run, with the daily rewrite re-read recorded."""
    return ReleaseCheckOnce(build_release_time_recorder(), RereadLog(PARTICIPANT_OI_REREADS))


def build_participant_oi_rule() -> AvailabilityRule:
    """When a decision may use a day's participant-OI file: set from the committed release-time evidence, and never
    before the bytes held were last written (judge 15: NSE rewrote 105 of 1,929 files after publishing them)."""
    checks, calendar = ReleaseLog(PARTICIPANT_OI_RELEASE_LOG).checks(), build_session_calendar()
    rule = choose_availability_rule(checks, calendar, DESK_DECISION_TIME)
    return LastWriteBoundRule(rule, calendar, DESK_DECISION_TIME, participant_oi_last_writes())


def participant_oi_last_writes() -> dict[date, datetime]:
    """Day -> the latest write time NSE reported for its participant-OI file, from every committed record."""
    checks = ReleaseLog(PARTICIPANT_OI_RELEASE_LOG).checks()
    table = read_last_modified_table(PARTICIPANT_OI_LAST_MODIFIED)
    return latest_writes(table, last_written_times(checks), read_sweeps(PARTICIPANT_OI_SWEEPS))


def build_last_write_sweep(archive: RevisionArchive, log: Path | None = None) -> LastWriteSweep:
    """Judge 16: a pass over every recorded participant-OI file, straight to NSE (never Drive); story A11: each file is
    read in full and a version that differs from the archived one is saved as a revision."""
    source = build_revision_capturing_source(ParticipantOiSource, archive)
    return LastWriteSweep(source, ParticipantOiSource.path_for, log or PARTICIPANT_OI_SWEEPS)  # O6: Actions' own log
