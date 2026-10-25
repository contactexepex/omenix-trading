"""Composition root of G7b completion's live capture (part b2; apart from `wiring.py`, at its size): G10's released
pack through `ReleasedPacks`, NSE's listed expiries, the history the ratios are fitted on, both W3 yardsticks on their
stored monthly ratios, V4's and V5's stored terms and outcomes (through G8's one Drive seam, `build_drive_records`),
A16's live rows, and O9's data store for every write."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime

from ..constants import NIFTY_SYMBOL, V1_RV_1S, V2_RV_5S, V3_RV_20S, V4_DAY_A, V4_RV_BELOW_WEEKLY_IV, V5_INSIDE_STRADDLE
from ..forecast_v4.pricing import V4_RISK_FREE_RATE
from ..forecast_v4.terms import HORIZON_SESSIONS
from ..intraday.candle_rv_table import CandleRvTable
from ..intraday.rv_table import RvTable
from ..intraday.wiring import INTRADAY_FOLDER
from ..quotes.expiry_listing import ExpiryListUnavailable, NseDailyFileExpiries
from ..research_engine.implied_vol import Black76
from ..storage.creation_times import CreationTimes
from ..storage.data_wiring import DATA_AREA, build_data_store
from ..storage.wiring import build_nse_fo_library, build_session_calendar
from ..v4_pack.release import NotReleased, ReleasedPacks
from ..v4_pack.wiring import build_released_packs
from . import series
from .baselines import Ewma
from .candle_history import CandleSession, candle_sessions, drift_days, paired_rv
from .implied import ImpliedBaselines, IvPoint, PremiumRatio, horizon_sums
from .intraday_series import RATIO_CLOSE_PROXY, RATIO_INTRADAY, backfill_window_points, intraday_horizon_rv
from .option_history import OUTCOMES_FOLDER, OptionHistory, outcome_from_bytes, terms_from_bytes
from .option_outcomes import V5Resolver
from .option_terms import OptionTermsRule
from .pack_adapter import POINTS_PER_UNIT, pack_inputs
from .pack_capture import TERMS_FOLDER, PackForecasts, PackInputs, store_refit_ratios
from .pack_followups import (
    DRIFT_FOLDER,
    W8_REVIEW_FOLDER,
    resolve_pending_v5,
    review_w8,
    write_drift_pairs,
)
from .ratio_store import StoredRatio
from .wiring import PACK_METHOD_FILES, implied_history, method_sha256

CAPTURE_WRITER = "forecast-v4-capture-pack"  # the receipts' writer field
QUESTIONS = (V1_RV_1S, V2_RV_5S, V3_RV_20S)


def drive_files(folder: str) -> dict[str, bytes]:
    """A Drive folder's verified files by their path inside the data area (G8's seam, G10's `DriveRecords`)."""
    from ..forecast_scoring.v4.wiring import build_drive_records

    return {path.removeprefix(f"{DATA_AREA}/"): data for path, data in build_drive_records(folder).files().items()}


def drive_get(path: str) -> bytes | None:
    return drive_files(path).get(path)


def option_history(sessions: list[date]) -> OptionHistory:
    terms = {q: {t.day: t for t in map(terms_from_bytes, drive_files(f"{TERMS_FOLDER}/{q}").values())}
             for q in (V4_RV_BELOW_WEEKLY_IV, V5_INSIDE_STRADDLE)}  # fmt: skip
    outcomes = dict(map(outcome_from_bytes, drive_files(OUTCOMES_FOLDER).values()))
    rows = series.live_intraday_rv(RvTable(INTRADAY_FOLDER).rows())
    return OptionHistory(terms[V4_RV_BELOW_WEEKLY_IV], terms[V5_INSIDE_STRADDLE], outcomes, rows, sessions)


def live_rv() -> dict[date, float | None]:
    """A16's live session `RV_s` (None: a void session)."""
    return {r.day: r.value for r in series.live_intraday_rv(RvTable(INTRADAY_FOLDER).rows())}


def candle_history() -> list[CandleSession]:
    """A16b's committed candle history through W8's one reader (G14 reads it here, never the table)."""
    return candle_sessions(CandleRvTable(INTRADAY_FOLDER).rows())


def candle_rv() -> dict[date, float | None]:
    """A16b's back-filled candle-close session `RV_s` (None: a void session); never a forecast input (W8)."""
    return {s.day: s.rv_session for s in candle_history()}


def intraday_rv() -> tuple[dict[date, float | None], set[date]]:
    """Yardstick A's window measure (W8): A16's live rows, A16b's back-fill where A16 has no row; and the back-filled
    sessions. A live row, void included, is never overridden."""
    live, backfill = live_rv(), candle_rv()
    return {**backfill, **live}, set(backfill) - set(live)


def listed_expiries(day: date) -> list[date] | None:
    try:
        return NseDailyFileExpiries(build_nse_fo_library()).listed(NIFTY_SYMBOL, day)[0]
    except ExpiryListUnavailable:
        return None


@dataclass(frozen=True)
class PackCapture:
    forecasts: PackForecasts
    inputs: PackInputs
    get: Callable[[str], bytes | None]
    put: Callable[[str, bytes], None]
    eod: dict[date, IvPoint]  # the EOD IV30 proxy, for the drift pairs
    settled: list[str]  # the refit day's stored ratios and V5's outcomes, both settled before the day's rows
    refused: str | None = None  # the day has no release record (`NotReleased`): no row, the rest still settled


def build_pack_capture(day: date, env: Mapping[str, str] = os.environ) -> PackCapture:
    """The day's capture. Before the release is read: a refit day's ratios are stored (judge 598 SF1, whatever the
    release) and V5's pending outcomes are settled (so its base rate counts them); then the forecasts, the inputs
    from the released pack (none, with `refused`, when the day has no release record) and get/put."""
    eod, closes, sessions = implied_history()
    put = build_data_store(CAPTURE_WRITER, env=env).put
    close_rv, (intraday, backfilled) = series.close_proxy_rv(closes), intraday_rv()

    def yardstick(measure: str, outcomes_of, labelled) -> dict[str, ImpliedBaselines]:
        return {
            q: ImpliedBaselines(HORIZON_SESSIONS[q], sessions, StoredRatio(
                PremiumRatio(eod, outcomes_of(HORIZON_SESSIONS[q])), q, measure, day, drive_get, put,
                frozenset(labelled(HORIZON_SESSIONS[q]))))
            for q in QUESTIONS
        }  # fmt: skip

    implied = {
        RATIO_CLOSE_PROXY: yardstick(RATIO_CLOSE_PROXY, lambda h: horizon_sums(close_rv, h), lambda h: ()),
        RATIO_INTRADAY: yardstick(
            RATIO_INTRADAY,
            lambda h: intraday_horizon_rv(intraday, sessions, h),
            lambda h: backfill_window_points(sessions, h, backfilled),
        ),  # fmt: skip
    }
    refit = store_refit_ratios(implied, day, sessions)
    history = option_history(sessions)
    settled, written = resolve_pending_v5(history, v5_resolver(env).resolve, put)
    v4, v5 = history.with_v5_outcomes(written).base_outcomes()
    rule = OptionTermsRule(Black76(), V4_RISK_FREE_RATE, build_session_calendar())
    forecasts = PackForecasts(implied, Ewma(close_rv), rule, {V4_RV_BELOW_WEEKLY_IV: v4, V5_INSIDE_STRADDLE: v5},
                              method_sha256(PACK_METHOD_FILES))  # fmt: skip
    try:
        inputs, refused = released_inputs(build_released_packs(env), day), None
    except NotReleased as missing:
        inputs, refused = None, str(missing)
    return PackCapture(forecasts, inputs, drive_get, put, eod, refit + settled, refused)


def released_inputs(released: ReleasedPacks, day: date) -> PackInputs:
    """`ReleasedPacks.release` raises `NotReleased` when the day has no release record."""
    release = released.release(day)
    if release.label != V4_DAY_A:
        return pack_inputs(release, None, b"", None)
    data = released.pack_bytes(release)
    return pack_inputs(release, released.pack(release), data, listed_expiries(day))


def v5_resolver(env: Mapping[str, str]) -> V5Resolver:
    """E7's final settlement, dated by Drive's created time (or none without the owner's Drive) and A8's log."""
    from ..desk.settlement import NseFinalSettlement
    from ..forecast_lab.wiring import RELEASE_FOLDER, RELEASE_LOG
    from ..research_data.release_times import ReleaseLog, first_seen_times
    from ..storage.creation_times import GoogleDriveCreationTimes
    from ..storage.wiring import RAW_AREA, build_owner_drive

    drive = build_owner_drive(env)
    created = GoogleDriveCreationTimes(drive, RAW_AREA) if drive is not None else NoCreationTimes()
    sightings = lambda: first_seen_times(ReleaseLog(RELEASE_FOLDER / "fo-bhavcopy" / RELEASE_LOG).checks())  # noqa: E731
    return V5Resolver(NseFinalSettlement(build_nse_fo_library()), created, sightings)


def run_followups(day: date, eod: dict[date, IvPoint], put: Callable) -> list[str]:
    """The proxy-drift pairs and W8's review trigger (`pack_followups`): what each capture run also settles."""
    from ..composition import build_alert_sender

    written = {date.fromisoformat(p.rsplit("/", 1)[1].removesuffix(".json")) for p in drive_files_paths(DRIFT_FOLDER)}
    days = write_drift_pairs(released_iv30(written), eod, written, put)
    lines = [f"proxy drift: {len(days)} day(s) paired"] if days else []
    raised = bool(drive_files_paths(W8_REVIEW_FOLDER))
    pairs = drift_days(paired_rv(live_rv(), candle_rv()))
    return lines + review_w8(day, pairs, raised, put, build_alert_sender().send)


def drive_files_paths(folder: str) -> list[str]:
    from ..forecast_scoring.v4.wiring import build_drive_records

    return build_drive_records(folder).paths()


def released_iv30(skip: set[date]) -> dict[date, IvPoint | None]:
    """Each released (A) day's pack IV30 as a fraction, read only for days not paired yet."""
    from ..v4_pack.paths import DAYS_FOLDER
    from ..v4_pack.release import parse_release

    released, found = build_released_packs(), {}
    for path, data in drive_files(DAYS_FOLDER).items():
        record = parse_release(path.rsplit("/", 1)[1].removesuffix(".json"), data)
        if record.label == V4_DAY_A and record.day not in skip:
            iv30 = released.pack(record).iv30
            found[record.day] = IvPoint(iv30.value / POINTS_PER_UNIT, iv30.flagged)
    return found


class NoCreationTimes(CreationTimes):
    """Without the owner's Drive settings: no created time, so A8's sighting (or nothing) dates a V5 outcome."""

    def created_at(self, path: str) -> datetime | None:
        return None
