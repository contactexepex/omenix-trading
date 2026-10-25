"""Composition root of the daily run (story O1): E3's desk run (Book 1's orders and exit rules) with O1's steps
around it: A14c's margin check, the weather, the v4 forecasts and the card as their own commands, each from its
`daily.live_from` date; Book 1's decision (E5) right after the pack, the AI books' fire just before it and their
collection after it, each AI book from its own `daily.live_from` date with its own orders and exit rules (story F1t);
the market school's slot (MS-P1j, its own
`school.enabled` switch); and A4c's quote parts beside the desk, committed through E3's committer in the run's one
thread."""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import date
from pathlib import Path

from ..config import ROOT
from ..constants import (
    BOOK1_RULES,
    BOOK2_HYBRID,
    BOOK3_AI,
    CARD_DELIVERIES_FOLDER,
    OWNER_TIMING_STEP,
    PLAYBOOK_FOLDER,
    REVIEWS_STEP,
    SCHOOL_STEP,
    V4_PACK_FORECASTS_STEP,
    V4_PACK_LIVE_KEY,
)
from ..desk.daily_ports import DayStep
from ..desk.daily_run import RERUN_FINAL
from ..school.constants import SLOT_LAST_START
from .runner import DayRunner

V4_RECORDS = "research/forecasts/v4/"  # G7's rows and M1's weather records (`fno/forecast_v4_rules/wiring.py`)
WEATHER = ("weather", "capture")  # today only, before its cutoff
FORECASTS_V4 = ("forecast-v4", "capture")  # today only, before its cutoff
FORECASTS_V4_PACK = ("forecast-v4", "capture-pack")  # G7b completion: today's pack-derived rows, by 15:10
# G7b completion's Drive folders, whose receipts its step commits
PACK_RECORD_FOLDERS = ("v4/records/live", "v4/terms", "v4/ratios", "v4/outcomes", "v4/diagnostics")
MARGIN_CHECK = ("margins", "stress-broker-check")  # A14c: idempotent, read-only Groww, done long before 14:55
MARGIN_CHECKS = "research/data/margins/stress_broker_check.csv"  # the one file it appends to (A14c builder, 15 Oct)
# MS-P1j2: why a failed school step stays failed (orchestrator, 24 Oct: no retry, a named reason)
SCHOOL_STARTS_BY = SLOT_LAST_START  # MS-P1j2/j3: the runner's own cutoff too; a run takes ~2-4 min (reasoning only)
SCHOOL_NOT_RETRIED = "; " + RERUN_FINAL.format(why="a later run never decides the session's paper trades")
FULL_LOG_WRITER = "daily-run"  # the receipts' writer name for the full log's Drive copy (O9)
LIVE_STEPS = ("margin_check", "weather", "forecasts_v4", V4_PACK_LIVE_KEY, V4_PACK_FORECASTS_STEP, "card",
              OWNER_TIMING_STEP, "price_distribution", "premium_ranges", "price_distribution_scores", "price_ranges",
              "price_range_scores", "premium_range_scores", "close_read", "close_recheck", "recommend")  # fmt: skip
LIVE_BOOKS = (BOOK2_HYBRID, BOOK3_AI)  # story F1t: each AI book's first trading day; null: not in the desk at all
OTHER_LIVE_KEYS = ("ai_books_v4",)  # G11's key, read by `fno/ai/wiring.py`
DISTRIBUTION_SCORES, RANGE_SCORES = ("pricedist", "score"), ("pricerange", "score")  # every resolved row, rescanned
PREMIUM_SCORES = ("premrange", "score")  # G13d: every issue whose next session has passed, and the seals


def range_issue(day: date) -> tuple[str, ...]:
    """G13b's live 15:45 issue (O1's `price_ranges` step)."""
    return ("pricerange", "issue", "--at", "1545", "--day", day.isoformat(), "--live")


def premium_issue(day: date) -> tuple[str, ...]:
    """G13d's live issue from G13's 3 pm record (O1's `premium_ranges` step; refuses itself after 15:30)."""
    return ("premrange", "issue", "--day", day.isoformat(), "--live")


def recommend_decide(day: date) -> tuple[str, ...]:
    """REC1b's step: it commits and pushes its own receipt before it posts, so the step names no folder."""
    return ("recommend", "decide", "--on", day.isoformat())


def school_run(day: date) -> tuple[str, ...]:
    """MS-P1j's slot: it seals, fills and commits its own records; with `school.enabled` off it prints "school off"."""
    return ("school", "run", "--session", day.isoformat())


def live_dates(cfg: dict) -> dict[str, date | None]:
    """`daily.live_from`: each O1 step's first live date; a step without one is not live."""
    raw = cfg.get("daily", {}).get("live_from", {}) or {}
    return {name: date.fromisoformat(str(raw[name])) if raw.get(name) else None for name in LIVE_STEPS}


def live_ai_books(cfg: dict, day: date) -> tuple[str, ...]:
    """The AI books live on `day` (`daily.live_from.<book>` on or before it); a key `daily.live_from` does not know is
    refused, so a typo can never leave a book silently off (O1 builder, 16 Oct)."""
    raw = cfg.get("daily", {}).get("live_from", {}) or {}
    known = (*LIVE_STEPS, *LIVE_BOOKS, *OTHER_LIVE_KEYS)
    unknown = sorted(set(raw) - set(known))
    if unknown:
        raise ValueError(f"config.yaml daily.live_from: unknown {', '.join(unknown)}; known: {', '.join(known)}")
    return tuple(b for b in LIVE_BOOKS if raw.get(b) and date.fromisoformat(str(raw[b])) <= day)


def build_day_runner(cfg: dict, root: Path = ROOT, sleep: Callable[[float], None] = time.sleep,
                     day: date | None = None) -> DayRunner:  # fmt: skip
    """`sleep` is how the run waits (story O2: the end-to-end suite drives the whole day on a fake clock); `day`: the
    session the run is for (its AI books are those live that day; none when not given, story F1t)."""
    from ..ai_trading.book_dispatch import ExitRulesByBook, OrdersByBook
    from ..ai_trading.wiring import ai_day_steps
    from ..books.book1_wiring import build_book1_exit_rules, build_book1_orders
    from ..close_read.constants import CLOSE_READ_FROM, CLOSE_RECHECK_FROM
    from ..close_read.wiring import receipt_pathspecs as close_receipts
    from ..composition import build_alert_sender
    from ..desk.daily_wiring import build_daily_run
    from ..desk.git_limit import GitLocks
    from ..desk.git_sync import Git, GitCommitter
    from ..desk.own_commits import OWN_UNPUSHED_FILE, OwnUnpushed
    from ..desk.owner_timing.wiring import build_owner_timing_desks, build_owner_timing_step
    from ..desk.wiring import build_entry_desk, build_execution_snapshots
    from ..intraday.backfill_daily import CATCH_UP_COMMAND, CATCH_UP_FROM, candle_folders
    from ..models import now_ist
    from ..premium_ranges.folders import receipt_pathspecs as premium_receipts
    from ..price_distribution.folders import receipt_pathspecs
    from ..price_ranges.folders import receipt_pathspecs as range_receipts
    from ..rehearsal.exercised_parts import rehearsed_quotes_done
    from ..rehearsal.live_wiring import rehearsed_live, rehearsed_not_live
    from ..rehearsal.v4_pack import rehearsed_part_processes
    from ..rehearsal.waits import rehearsed_waiter
    from ..scorecard.wiring import build_scorecard_run
    from .alerts import ReportedAlerts
    from .earlier_run import PartMarkers
    from .history import WholeHistory
    from .part_locks import PART_LOCKS, PartLocks
    from .processes import ChildProcesses
    from .quote_parts import QuoteParts
    from .quote_steps import FinishQuoteParts, ServicingWaiter, StartQuoteParts
    from .reviews import ReviewsStep, ScorecardReview
    from .steps import Alerted, CommandStep, LiveFrom, NotBefore, StartsBy
    from .v4_wiring import day_parts, part_notes, step_notes, v4_steps
    from .v4_wiring import receipts as v4_receipts
    from .wait_notice import AnnouncedWaiter

    git, alerts, processes, (live, not_live) = (
        Git(root),
        ReportedAlerts(build_alert_sender()),
        ChildProcesses(root),
        rehearsed_live(live_dates(cfg)),  # story REH1c: every report runs in a rehearsal, and says if not live
    )
    locks = GitLocks(root)  # story O2: a command stopped at its limit leaves no git lock behind
    committer = GitCommitter(git, OwnUnpushed(root / OWN_UNPUSHED_FILE))  # the run's one: G4
    quote_parts = day_parts(cfg)  # A4's 3 pm parts and G10's `v4` capture
    parts = QuoteParts(quote_parts, rehearsed_part_processes(processes, part_notes(quote_parts, not_live)), committer,
                       git.changed, alerts, now_ist, PartLocks(root / PART_LOCKS), PartMarkers(root, git),
                       live)  # fmt: skip
    announced = AnnouncedWaiter(ServicingWaiter(parts, now_ist, sleep), now_ist, lambda line: print(line, flush=True))
    waiter = rehearsed_waiter(announced, parts)  # story REH1: a rehearsal skips the waits outside the windows

    def waiting(seconds: float) -> None:
        """A command's wait: a quote part due meanwhile starts (no git: the commits stay between the steps)."""
        sleep(seconds)
        parts.start_due()

    def command(arguments: Callable[[date], tuple[str, ...]], folder: str) -> DayStep:
        return CommandStep(processes, arguments, (folder,), git.changed, waiting, locks)

    card = command(lambda day: ("card", "daily", "--on", day.isoformat(), "--post"), CARD_DELIVERIES_FOLDER)
    price_distribution = CommandStep(processes, lambda day: ("pricedist", "record", "--day", day.isoformat(), "--live"),
                                     receipt_pathspecs(), git.changed, waiting, locks)  # fmt: skip
    price_ranges = CommandStep(processes, range_issue, range_receipts(), git.changed, waiting, locks)
    premium_ranges = CommandStep(processes, premium_issue, premium_receipts(), git.changed, waiting, locks)

    def close_step(name: str, arguments: tuple[str, ...], gate) -> DayStep:
        """A4h's reads: LiveFrom outside NotBefore (a day before the live date never waits), its receipts only."""
        step = CommandStep(processes, lambda day: arguments, close_receipts(), git.changed, waiting, locks)
        return Alerted(name, LiveFrom(NotBefore(step, gate, waiter), live[name]), alerts)

    def scores(arguments: tuple[str, ...], pathspecs: tuple[str, ...], name: str) -> DayStep:
        """G13's, G13b's and G13d's scorers: their own receipts only (the scores file; G13b's and G13d's seals too)."""
        step = CommandStep(processes, lambda day: arguments, pathspecs, git.changed, waiting, locks)
        return Alerted(name, LiveFrom(step, live[name]), alerts)

    ai_books, ai_steps, book_parts = ai_day_steps(cfg, root, day, alerts, processes, waiter, git, committer,
                                                   now_ist)  # fmt: skip
    finish_parts = rehearsed_quotes_done(FinishQuoteParts(parts, waiter), quote_parts, not_live)  # REH1j: live parts
    steps = {
        "margin_check": Alerted(
            "margin_check", LiveFrom(command(lambda day: MARGIN_CHECK, MARGIN_CHECKS), live["margin_check"]), alerts
        ),  # A14c's command does not exist yet: live from the date its code lands
        "weather": Alerted("weather", LiveFrom(command(lambda day: WEATHER, V4_RECORDS), live["weather"]), alerts),
        "forecasts_v4": Alerted(
            "forecasts_v4", LiveFrom(command(lambda day: FORECASTS_V4, V4_RECORDS), live["forecasts_v4"]), alerts
        ),  # fmt: skip
        V4_PACK_FORECASTS_STEP: Alerted(
            V4_PACK_FORECASTS_STEP,
            LiveFrom(
                CommandStep(
                    processes,
                    lambda day: FORECASTS_V4_PACK,
                    v4_receipts(*PACK_RECORD_FOLDERS),
                    git.changed,
                    waiting,
                    locks,
                ),
                live[V4_PACK_FORECASTS_STEP],
            ),
            alerts,
        ),  # G7b completion: its own receipts only  # fmt: skip
        "quotes": Alerted("quotes", StartQuoteParts(parts), alerts),
        **{name: Alerted(name, step, alerts) for name, step in ai_steps.items()},  # story F1t
        "book1": Alerted(
            "book1",
            CommandStep(
                processes, lambda day: ("desk", "book1", "--day", day.isoformat()), (), git.changed, waiting, locks
            ),
            alerts,
        ),  # E5: commits its own decision  # fmt: skip
        REVIEWS_STEP: Alerted(
            REVIEWS_STEP,
            ReviewsStep(
                (ScorecardReview(build_scorecard_run(cfg, root, alerts)),),
                build_execution_snapshots(),
                root,
                git.changed,
                (f"{PLAYBOOK_FOLDER}/",),
            ),
            alerts,
        ),  # E6's pauses  # fmt: skip
        "quotes_done": Alerted("quotes_done", finish_parts, alerts, status_alerts=False),
        "card": Alerted("card", LiveFrom(card, live["card"]), alerts),
        "price_distribution": Alerted(
            "price_distribution", LiveFrom(price_distribution, live["price_distribution"]), alerts
        ),  # G13: its own receipts only  # fmt: skip
        "premium_ranges": Alerted("premium_ranges", LiveFrom(premium_ranges, live["premium_ranges"]), alerts),  # G13d
        SCHOOL_STEP: Alerted(
            SCHOOL_STEP,
            StartsBy(CommandStep(processes, school_run, (), git.changed, waiting, locks), SCHOOL_STARTS_BY, now_ist),
            alerts,
            note=SCHOOL_NOT_RETRIED,
        ),  # MS-P1j2: never started late, never retried
        "recommend": Alerted(
            "recommend",
            LiveFrom(CommandStep(processes, recommend_decide, (), git.changed, waiting, locks), live["recommend"]),
            alerts,
            status_alerts=False,  # the command alerts each failure itself; a raise is still alerted here
        ),  # REC1b: it commits its own receipt, so no pathspec
        "price_distribution_scores": scores(DISTRIBUTION_SCORES, receipt_pathspecs(), "price_distribution_scores"),
        "price_ranges": Alerted("price_ranges", LiveFrom(price_ranges, live["price_ranges"]), alerts),  # G13b
        "price_range_scores": scores(RANGE_SCORES, range_receipts(), "price_range_scores"),
        "premium_range_scores": scores(PREMIUM_SCORES, premium_receipts(), "premium_range_scores"),
        "candles": Alerted(
            "candles",
            NotBefore(
                CommandStep(processes, lambda day: CATCH_UP_COMMAND, candle_folders(), git.changed, waiting, locks),
                CATCH_UP_FROM,
                waiter,
            ),
            alerts,
        ),  # A16b-d: yesterday's candles, after A16's last mark
        "close_read": close_step("close_read", ("closes", "read"), CLOSE_READ_FROM),  # A4h
        "close_recheck": close_step("close_recheck", ("closes", "read", "--recheck"), CLOSE_RECHECK_FROM),
    }
    cfg_orders = OrdersByBook(
        {BOOK1_RULES: build_book1_orders(cfg, root), **{b: p.orders for b, p in book_parts.items()}}
    )
    exit_rules = ExitRulesByBook(
        {BOOK1_RULES: build_book1_exit_rules(root, alerts), **{b: p.exits for b, p in book_parts.items()}}
    )
    entry_desk, exit_timing = build_owner_timing_desks(cfg, live[OWNER_TIMING_STEP], build_entry_desk(cfg))
    fills = build_owner_timing_step(cfg, alerts, exit_timing, live[OWNER_TIMING_STEP], root=root)
    steps[OWNER_TIMING_STEP] = Alerted(OWNER_TIMING_STEP, fills, alerts)  # E8: seals only before its live date
    steps |= v4_steps(lambda arguments, specs: CommandStep(processes, arguments, specs, git.changed, waiting, locks),
                      parts, waiter, live[V4_PACK_LIVE_KEY], alerts)  # G10 completion  # fmt: skip
    steps = rehearsed_not_live(steps, step_notes(not_live))
    daily_run = build_daily_run(cfg, cfg_orders, exit_rules, books=(BOOK1_RULES, *ai_books), root=root,
                                waiter=waiter, day_steps=steps, git=git,
                                alerts=alerts, entry_desk=entry_desk, exit_timing=exit_timing,
                                git_committer=committer, recorder=public_recorder(root))  # fmt: skip
    archive = full_log_archive(root, committer, alerts)
    return DayRunner(daily_run, parts, waiter, WholeHistory(git, alerts), archive.archive)


def public_recorder(root: Path):
    """Story O1-status-only: the committed run log holds status only; the full text stays in the private log."""
    from .full_log import FULL_LOGS, FullRunLog, PublicRecorder
    from .public_log import PublicResult, ReasonRegistry
    from .reason_codes import COMMON, STEP_TEMPLATES

    return PublicRecorder(PublicResult(ReasonRegistry(COMMON, STEP_TEMPLATES)), FullRunLog(root / FULL_LOGS))


def full_log_archive(root: Path, committer, alerts):
    """The full log's write-once Drive copy (O9's data store), its receipt in this checkout's `receipts/`."""
    from ..storage import wiring as storage
    from ..storage.data_store import DataStore, new_run_id
    from ..storage.data_wiring import DATA_AREA, RECEIPTS_FOLDER
    from ..storage.receipts import ReceiptFolder
    from .full_log import FULL_LOGS, FullRunLog
    from .full_log_archive import DriveNotSet, FullLogArchive

    def store() -> DataStore:
        drive = storage.build_owner_drive()
        if drive is None:
            raise DriveNotSet()
        return DataStore(drive, DATA_AREA, ReceiptFolder(root / RECEIPTS_FOLDER), FULL_LOG_WRITER, new_run_id())

    return FullLogArchive(FullRunLog(root / FULL_LOGS), store, committer, alerts)
