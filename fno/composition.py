"""Composition root of the F&O app: the only place that picks concrete classes for the app's services (raw data stores
and sources are wired in `fno/storage/wiring.py`). Swapping a provider or store changes this file only."""

from __future__ import annotations

import hashlib
import json
import os
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy

from .alerts.sender import AlertSender, NoAlertSender, SlackChannelAlerts
from .books.account import AccountWriter, PaperAccount
from .books.lock import DEFAULT_LEASE_SECONDS, AccountLock
from .books.version_registry import VersionRegistry
from .books.versions import VERSIONS_FILE, Versions
from .config import ROOT
from .constants import (
    DESK_DECISION_TIME,
    ENV_FNO_SLACK_BOT_TOKEN,
    FNO_DESK_CHANNEL_ID,
    NIFTY_SYMBOL,
    OPTION_CALL,
    OPTION_PUT,
    STRUCTURE_CALL_CREDIT_SPREAD,
    STRUCTURE_CALL_DEBIT_SPREAD,
    STRUCTURE_LONG_CALL,
    STRUCTURE_LONG_PUT,
    STRUCTURE_PUT_CREDIT_SPREAD,
    STRUCTURE_PUT_DEBIT_SPREAD,
)
from .providers import AUTO_PROVIDER, get_provider
from .providers.base import Provider
from .providers.nse_quotes import NseQuoteProvider
from .providers.public import PublicData
from .quotes.expiry_listing import NseDailyFileExpiries
from .quotes.market_levels import NseLevelSource
from .quotes.recorder import DATASET as GROWW_QUOTE_DATASET
from .quotes.recorder import NSE_DATASET as NSE_QUOTE_DATASET
from .quotes.recorder import QuoteSnapshotRecorder
from .record_scan.wiring import build_record_scanner  # noqa: F401 - re-exported: the scan's root is stdlib-only (DR1)
from .research_data.availability import AvailabilityRule, LastWriteBoundRule
from .research_data.events import read_events
from .research_data.last_written import latest_writes, read_last_modified_table
from .research_data.panel_reader import NiftyPanel, read_nifty_panel
from .research_data.positioning import PointInTimeParticipantOi
from .research_data.quote_snapshots import RecordedSnapshots
from .research_data.release_check_once import ReleaseCheckOnce
from .research_data.release_times import ReleaseLog, ReleaseTimeRecorder, choose_availability_rule, last_written_times
from .research_data.reread_log import RereadLog
from .research_data.write_sweep import LastWriteSweep, read_sweeps
from .research_engine.cycle_costs import CycleTerms
from .research_engine.cycles import EXIT_MIN_DAYS, Cycle, TradingDays, cycle_rows, monthly_cycles
from .research_engine.event_features import ScheduledEventInWindow
from .research_engine.experiments import Period
from .research_engine.features import DecisionContext, Feature, ResearchData
from .research_engine.implied_vol import Black76
from .research_engine.ledger import Git, Ledger
from .research_engine.live_features import LiveAtmIvMinusRealised, LiveScheduledEventInWindow, LiveVixAboveMedian
from .research_engine.live_validation import ValidationReport, validate
from .research_engine.one_side import BoughtOption, VerticalSpread
from .research_engine.runner import ExperimentRunner
from .research_engine.simulator import CycleSimulator
from .research_engine.structures import BOUGHT, SOLD, LongIronFly, ShortCondor, ShortIronFly, Structure
from .research_engine.trial_guard import LedgerTrialGuard
from .research_engine.volatility_features import AtmIvMinusRealised, VixAboveMedian
from .storage.raw_source import ParticipantOiSource
from .storage.revisions import RevisionArchive
from .storage.wiring import (
    CALENDAR_FILE,
    EVENTS_FILE,
    PANEL_FOLDER,
    PARTICIPANT_OI_LAST_MODIFIED,
    PARTICIPANT_OI_RELEASE_LOG,
    PARTICIPANT_OI_REREADS,
    PARTICIPANT_OI_SWEEPS,
    build_nse_fo_library,
    build_nse_source,
    build_participant_oi_library,
    build_quote_store,
    build_revision_capturing_source,
    build_session_calendar,
)


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
    from .rehearsal.quote_wiring import rehearsed_recorder

    expiries, levels = NseDailyFileExpiries(build_nse_fo_library()), NseLevelSource(PublicData().nse_json)
    return rehearsed_recorder(
        QuoteSnapshotRecorder(
            provider,
            build_quote_store(),
            fallback=expiries,
            calendar=build_session_calendar(),
            history=expiries,
            levels=levels,
            dataset=dataset,
        )
    )  # fmt: skip; story REH1b: the day's recorded attempts when rehearsing


@contextmanager
def open_account_writer(book: str, root: Path = ROOT, lease_seconds: float = DEFAULT_LEASE_SECONDS, files=None):
    """The one way to write a book's paper account (story E1): takes the book's single-writer lock without waiting
    (`AccountBusy` if another writer holds it) and yields the account's writer; the lock is released on exit. With
    `files` (story E2c, the private records in Drive), the account is pulled once the lock is held and pushed when the
    write ends without an error."""
    with AccountLock(root, book, lease_seconds) as lock:
        if files is not None:
            files.pull_account(book)
        yield AccountWriter(PaperAccount(root, book), lock, paper_account_rs())
        if files is not None:
            files.push_account(book)


def paper_account_rs() -> float:
    """Story C5: the books' paper account size, `config.yaml` `risk.profiles.books.paper_account_rs`."""
    from .config import load_app_config
    from .constants import RISK_PROFILE_BOOKS
    from .risk.profile_settings import profile_settings

    return profile_settings(load_app_config(), RISK_PROFILE_BOOKS).paper_account_rs


def build_paper_account(book: str, root: Path = ROOT) -> PaperAccount:
    """Read-only view of a book's paper account."""
    return PaperAccount(root, book)


def build_version_registry(root: Path = ROOT) -> VersionRegistry:
    """Story D6: the books' append-only version registry, `journal/versions.csv`."""
    return VersionRegistry(root / VERSIONS_FILE)


def build_versions(root: Path = ROOT) -> Versions:
    """Story D6: the registered versions, with git deciding when each row was committed."""
    return Versions(build_version_registry(root).rows(), Git(root))


def build_alert_sender() -> AlertSender:
    """Alerts go to #fno-desk with `FNO_SLACK_BOT_TOKEN`; without it, nothing is sent and the outcome says so."""
    from .rehearsal.alert_label import rehearsed_alerts

    token = os.environ.get(ENV_FNO_SLACK_BOT_TOKEN)
    return rehearsed_alerts(SlackChannelAlerts(token, FNO_DESK_CHANNEL_ID) if token else NoAlertSender())


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


def build_point_in_time_participant_oi(project_folder: Path | None = None) -> PointInTimeParticipantOi:
    """Participant OI as a decision at a given moment could have known it (story A8)."""
    library = build_participant_oi_library(project_folder)
    return PointInTimeParticipantOi(
        lambda day: library.get(ParticipantOiSource.path_for(day)).data,
        ParticipantOiSource.filename_for,
        build_session_calendar(),
        build_participant_oi_rule(),
    )


def build_features(cfg: dict) -> tuple[Feature, ...]:
    """Experiment 1's daily-close features (story B1). F1 prices on the same-expiry future with Black-76 (story B1 note
    of 13 Oct 2026); the `risk_free_rate` setting only discounts."""
    return (AtmIvMinusRealised(Black76(), cfg["risk_free_rate"]), VixAboveMedian(), ScheduledEventInWindow())


def load_research_data(years=None, keep=None) -> ResearchData:
    """The repository's NIFTY panel (story A3; `years` and `keep` as in `read_nifty_panel`) and events calendar (A6)."""
    return ResearchData(read_nifty_panel(PANEL_FOLDER, years, keep), tuple(read_events(EVENTS_FILE.read_text())))


def build_cycles(panel: NiftyPanel) -> list[Cycle]:
    """Experiment 1's monthly cycles of the panel (story B2): A5's monthly rule and NSE's session calendar (A1)."""
    return monthly_cycles(panel, build_session_calendar())


def build_structures() -> tuple[Structure, ...]:
    """Experiment 1's structures SF, SC and BF (story B2)."""
    return ShortIronFly(), ShortCondor(), LongIronFly()


def build_tradable_structures() -> tuple[Structure, ...]:
    """Every structure the desk may build (D2) and A14 gives margin rows: experiment 1's three, then the one- and
    two-leg ones of story STR1 (LC, LP, CDS, CCS, PDS, PCS)."""
    return (
        *build_structures(),
        BoughtOption(STRUCTURE_LONG_CALL, OPTION_CALL),
        BoughtOption(STRUCTURE_LONG_PUT, OPTION_PUT),
        VerticalSpread(STRUCTURE_CALL_DEBIT_SPREAD, OPTION_CALL, BOUGHT),
        VerticalSpread(STRUCTURE_CALL_CREDIT_SPREAD, OPTION_CALL, SOLD),
        VerticalSpread(STRUCTURE_PUT_DEBIT_SPREAD, OPTION_PUT, BOUGHT),
        VerticalSpread(STRUCTURE_PUT_CREDIT_SPREAD, OPTION_PUT, SOLD),
    )


def build_cycle_simulator(cfg: dict, panel: NiftyPanel) -> CycleSimulator:
    """Story B2's simulator: one NIFTY lot (`lot_sizes`) and the `charges` block of config.yaml; the protocol's pad,
    loss cap and widths."""
    return CycleSimulator(panel, CycleTerms(lot=cfg["lot_sizes"][NIFTY_SYMBOL], charges=cfg["charges"]))


def load_period_data(period: Period) -> ResearchData:
    """A period's research data (story B3): option and future rows only from the period's years (option rows from its
    first decision day on, and only those cycles use, 21+ days to expiry), plus a year after the end for late exits.
    The features' look-back before the period (F1: 21 closes, F2: 250) comes from the panel's index-close file (NSE's
    index-close files, story A10), so no earlier year's option file is ever opened (judge 28)."""
    years = range(period.start.year, period.end.year + 2)
    return load_research_data(years, keep=lambda day, expiry: day >= period.start and cycle_rows(day, expiry))


def research_inputs(cfg: dict) -> dict:
    """SHA-256 of every input a results file depends on, and the numpy version (its generator streams)."""

    files = {"panel_manifest": PANEL_FOLDER / "manifest.json", "events": EVENTS_FILE, "session_calendar": CALENDAR_FILE}
    terms = {key: cfg[key] for key in ("charges", "lot_sizes", "risk_free_rate")}
    return {
        **{name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in files.items()},
        "config_terms": hashlib.sha256(json.dumps(terms, sort_keys=True).encode()).hexdigest(),
        "numpy": numpy.__version__,
    }


def build_ledger(root: Path = ROOT) -> Ledger:
    return Ledger(root)


def build_experiment_runner(cfg: dict, root: Path = ROOT) -> ExperimentRunner:
    """Story B3's runner: B4's ledger guard, the repository's panel and events, B1's features, B2's cycles,
    structures and simulator."""
    ledger = build_ledger(root)
    return ExperimentRunner(
        guard=LedgerTrialGuard(ledger),
        load_data=load_period_data,
        build_cycles=build_cycles,
        features=build_features(cfg),
        structures=build_structures(),
        build_simulator=lambda panel: build_cycle_simulator(cfg, panel),
        ledger_count=ledger.count,
        inputs=lambda: research_inputs(cfg),
    )


LIVE_HISTORY_START = date(2026, 10, 1)  # before A4's first recorded day; days without a snapshot are skipped


def build_live_features(cfg: dict) -> tuple[Feature, ...]:
    """Story B7: the 15:00 versions of F1-F3, known at the desk's decision time, in the order of `build_features`."""
    cutoff = DESK_DECISION_TIME
    return (
        LiveAtmIvMinusRealised(cutoff, cfg["risk_free_rate"], Black76()),
        LiveVixAboveMedian(cutoff),
        LiveScheduledEventInWindow(cutoff),
    )


def validation_context(data: ResearchData, day: date) -> DecisionContext | None:
    """The context both versions are compared in: the day's farther recorded monthly expiry (the next monthly), entry
    the next trading day, exit the last trading day with 21 or more days to expiry (as story B2's cycles)."""
    snapshot = data.snapshots.get(day)
    if snapshot is None or not snapshot.expiries:
        return None
    days, expiry = TradingDays(build_session_calendar()), max(snapshot.expiries)
    return DecisionContext(expiry, days.next_after(day), days.last_on_or_before(expiry - timedelta(days=EXIT_MIN_DAYS)))


def run_live_validation(cfg: dict, live_name: str, today: date) -> ValidationReport:
    """Story B7's validation of one live feature against its research version over every recorded A4 day."""
    live_features = build_live_features(cfg)
    position = [f.name for f in live_features].index(live_name)
    live, close = live_features[position], build_features(cfg)[position]
    sessions = build_session_calendar().sessions(LIVE_HISTORY_START, today)
    data = load_research_data(range(LIVE_HISTORY_START.year - 1, today.year + 1), keep=cycle_rows)
    data = ResearchData(data.panel, data.events, RecordedSnapshots(build_quote_store()).snapshots(sessions))
    return validate(live, close, data, sessions, lambda day: validation_context(data, day))
