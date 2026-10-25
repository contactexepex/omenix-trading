"""Composition root of protocol v4's pack (story G10 part 2): the day's release run (A4e's v4 capture, G1 v2's live IV30
rule, O9's data store), the verified Drive cache behind the released packs, and GitHub's push receipts behind the
15:10 deadline."""

from __future__ import annotations

import hashlib
import os
from collections.abc import Mapping
from pathlib import Path

from ..ai.receipts import GitHubActivityReceipts
from ..config import ROOT
from ..constants import ENV_GITHUB_TOKEN, GITHUB_REPOSITORY_VARIABLE, V4_PACK_LIVE_KEY
from ..health.evidence import Evidence, HealthHistory
from ..quotes.window import V4_WINDOW
from ..storage.data_wiring import DATA_AREA, RECEIPTS_FOLDER, build_data_store, build_drive_cache
from .commitment import CommitmentTimes, GitHubCommitmentTimes
from .deadline import DeadlineRun
from .overlap import OverlapWatch
from .paths import LIVE_RECORDS_FOLDER
from .release import ReleasedPacks
from .release_run import ReleaseRun
from .sessions import sessions_between

V4_RECORDS = "research/forecasts/v4"  # G8's folder of CSV records (G7's rules, M1's weather)
RELEASE_WRITER, DEADLINE_WRITER = "v4-release", "v4-deadline"
IV30_METHOD = "g1_v2_live_atm_iv30"
# G1 v2's live ATM rule and interpolation, and the protocol's rate they run at (story G6 freeze, judge 597 SF1)
IV30_METHOD_FILES = ("research_engine/live_features.py", "forecast/iv30.py", "forecast_v4/pricing.py")


def iv30_method() -> str:
    """The IV30 method's name and the SHA-256 of its files' bytes, carried in every pack."""
    package = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256(b"".join((package / name).read_bytes() for name in IV30_METHOD_FILES)).hexdigest()
    return f"{IV30_METHOD}/sha256:{digest}"


def build_iv30_rule():
    """G1 v2's live ATM IV30 rule at the protocol's rate (`pricing.V4_RISK_FREE_RATE`), never the config's."""
    from ..forecast_v4.pricing import V4_RISK_FREE_RATE
    from ..research_engine.implied_vol import Black76
    from ..research_engine.live_features import LiveAtmIvMinusRealised

    return LiveAtmIvMinusRealised(None, V4_RISK_FREE_RATE, Black76())


def run_live_dates(cfg: dict, env: Mapping[str, str] = os.environ) -> dict:
    """`daily.live_from` as the daily run's root sees it: in a rehearsal a key not live on the replayed day is made
    live (REH1c), so the child exercises what its step was made live to do; a real run gets the dates unchanged."""
    from ..daily.wiring import live_dates
    from ..rehearsal.live_wiring import rehearsed_live

    return rehearsed_live(live_dates(cfg), env)[0]


def build_release_run(cfg: dict, env: Mapping[str, str] = os.environ) -> ReleaseRun:
    from ..forecast_v4.sessions import is_scored_session
    from ..models import now_ist
    from ..quotes.recorder import DATASET
    from ..quotes.window import named_window
    from ..storage.quote_wiring import build_drive_only_quote_store
    from ..storage.wiring import QUOTES_FOLDER, build_session_calendar
    from .builder import PackBuilder
    from .capture import StoredV4Capture

    dataset = named_window(cfg, V4_WINDOW).dataset(DATASET)
    capture = StoredV4Capture(build_drive_only_quote_store(QUOTES_FOLDER, env, dataset=dataset), dataset)
    rule = build_iv30_rule()
    calendar, store = build_session_calendar(), build_data_store(RELEASE_WRITER, env=env)

    from ..rehearsal.v4_pack import rehearsed_release_excuse

    sessions, live = sessions_between(lambda day: is_scored_session(calendar, day)), run_live_dates(cfg, env)
    builder = PackBuilder(rule, iv30_method(), now_ist)
    excuse = rehearsed_release_excuse(_recorded_v4(dataset), env)
    in_drive = lambda path: store.drive.get(path) is not None  # noqa: E731
    return ReleaseRun(store, in_drive, capture, builder, sessions, live[V4_PACK_LIVE_KEY], now_ist, excuse)  # fmt: skip


def build_deadline_run(cfg: dict, env: Mapping[str, str] = os.environ) -> DeadlineRun:
    """The 15:10 check of every live commitment, through GitHub's push receipts (F1, O8's evidence)."""
    from ..forecast_v4.sessions import is_scored_session
    from ..models import now_ist
    from ..rehearsal.v4_pack import rehearsed_catch_up
    from ..storage.wiring import build_session_calendar
    from .commitments import RecordCommitments

    calendar, store = build_session_calendar(), build_data_store(DEADLINE_WRITER, env=env)
    source = RecordCommitments(ROOT, V4_RECORDS, f"{RECEIPTS_FOLDER}/{DATA_AREA}/{LIVE_RECORDS_FOLDER}")
    in_drive = lambda path: store.drive.get(path) is not None  # noqa: E731
    sessions = sessions_between(lambda day: is_scored_session(calendar, day))
    live = run_live_dates(cfg, env)
    return DeadlineRun(store, in_drive, source, build_commitment_times(env=env), sessions, live[V4_PACK_LIVE_KEY],
                       now_ist, rehearsed_catch_up(env), live["forecasts_v4"])  # fmt: skip


def build_overlap_watch(cfg: dict) -> OverlapWatch:
    from ..quotes.recorder import DATASET
    from ..quotes.window import named_window
    from ..storage.wiring import QUOTES_FOLDER

    dataset = named_window(cfg, V4_WINDOW).dataset(DATASET)
    return OverlapWatch(QUOTES_FOLDER.joinpath(*dataset.split("/")), ROOT / "research" / "data" / "intraday")


def _recorded_v4(dataset: str):
    """Whether a checkout (the rehearsal's record) holds a `v4` attempt of a day: a sidecar in the dataset's folder."""
    from ..storage.wiring import QUOTES_FOLDER

    folder = QUOTES_FOLDER.relative_to(ROOT).joinpath(*dataset.split("/"))
    return lambda record, day: any(
        (record / folder / f"{day:%Y}" / f"{day:%m}").glob(f"nifty_{day:%Y%m%d}_*.meta.json")
    )


def build_released_packs(env: Mapping[str, str] = os.environ) -> ReleasedPacks:
    return ReleasedPacks(build_drive_cache(env), DATA_AREA)


def build_commitment_times(root: Path = ROOT, env: Mapping[str, str] = os.environ) -> CommitmentTimes:
    history = HealthHistory(Path(root))
    from ..rehearsal.receipts_wiring import rehearsed_receipts

    receipts = rehearsed_receipts(
        GitHubActivityReceipts(env.get(GITHUB_REPOSITORY_VARIABLE, ""), env.get(ENV_GITHUB_TOKEN, ""), history), history
    )  # REH1b: the rehearsal's push log
    return GitHubCommitmentTimes(Evidence(Path(root), history, receipts))
