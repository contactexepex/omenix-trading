"""Composition root of the AI books' trading runner, daily-run side (story F1t): the only place that picks the concrete
routine triggers, packs, budget signal, record scan, cards source and each book's parts. Each AI book's parts (its
decider, orders and exit rules) are its story's: F5 (Book 2) and F6 (Book 3) add one line each to `BOOK_PARTS`. The
routine side has its own root (`book_wiring.py`, standard library only)."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from ..alerts.sender import AlertSender
from ..constants import (
    BOOK2_HYBRID,
    BOOK3_AI,
    ENV_ROUTINE_BOOK2_DECISION_TOKEN,
    ENV_ROUTINE_BOOK2_DECISION_TRIGGER_ID,
    ENV_ROUTINE_BOOK3_DECISION_TOKEN,
    ENV_ROUTINE_BOOK3_DECISION_TRIGGER_ID,
)
from ..desk.daily_ports import ExitRules, OrderBuilder, Waiter
from ..pipeline.trigger import RoutineFireTrigger, RoutineTrigger, UnconfiguredTrigger
from .ports import AiBookDecider, AnalystCards, DayPacks, JudgeStep, NoAnalystCards
from .versions import REGISTRY

ROUTINES = {
    BOOK2_HYBRID: (ENV_ROUTINE_BOOK2_DECISION_TRIGGER_ID, ENV_ROUTINE_BOOK2_DECISION_TOKEN),
    BOOK3_AI: (ENV_ROUTINE_BOOK3_DECISION_TRIGGER_ID, ENV_ROUTINE_BOOK3_DECISION_TOKEN),
}  # book -> its decision routine's two settings in the daily routine's environment


@dataclass(frozen=True)
class BookParts:
    decider: AiBookDecider
    orders: OrderBuilder
    exits: ExitRules


PartsBuilder = Callable[[dict, Path, AlertSender], BookParts]
BOOK_PARTS: dict[str, PartsBuilder] = {}  # F5 and F6 add their book's builder here
JUDGE_STEP: Callable[[Path], JudgeStep] | None = None  # F4 sets its builder here (`fno/judge/wiring.py`)
FIRE_LOG_MARKER = ".pending_ai_fire.json"  # the fire log's pending commit, beside the run's own marker


def build_decision_trigger(book: str, env=os.environ) -> RoutineTrigger:
    names = ROUTINES[book]
    trigger_id, token = (env.get(name) for name in names)
    if not (trigger_id and token):
        return UnconfiguredTrigger(book, tuple(n for n in names if not env.get(n)))
    return RoutineFireTrigger(book, trigger_id, token)


def build_book_parts(cfg: dict, root: Path, alerts: AlertSender, books) -> dict[str, BookParts]:
    return {book: BOOK_PARTS[book](cfg, root, alerts) for book in books if book in BOOK_PARTS}


def build_day_packs(root: Path) -> DayPacks:
    from ..desk.common_pack import CommonPack
    from ..desk.pack_store import PackStore
    from ..desk.private_pack import PrivatePack

    store = PackStore(root)

    def private(book: str, day: date) -> PrivatePack:
        return PrivatePack(book, day, json.loads(store.private_path(book, day).read_text(encoding="utf-8")))

    return DayPacks(lambda day: CommonPack.read(day, store.common_path(day)), private)


def ai_day_steps(
    cfg: dict,
    root: Path,
    day: date | None,
    alerts: AlertSender,
    processes,
    waiter: Waiter,
    git,
    committer,
    clock: Callable[[], datetime],
) -> tuple[tuple[str, ...], dict, dict[str, BookParts]]:
    """The AI books live on the run's `day`, O1's two AI steps and each live book's parts, for the daily run's root.
    `committer`: the run's one (its own unpushed commits are accepted, O1's G4). One wrong AI setting stops the AI
    steps only, never the quotes or Book 1."""
    from ..daily.wiring import live_ai_books

    try:
        books, wrong = (live_ai_books(cfg, day) if day else ()), ""
    except ValueError as refused:
        books, wrong = (), str(refused)
    parts = build_book_parts(cfg, root, alerts, books)
    live_on = lambda run_day: books if run_day == day else ()  # noqa: E731 - the books live on the built day
    if not books and not wrong:  # nothing live: not_live, whatever the AI settings say (a bad timetable waits too)
        return books, not_live_steps(), parts
    steps = config_refused(wrong) if wrong else build_ai_steps(cfg, root, live_on, parts, processes, waiter, git,
                                                                committer, clock)  # fmt: skip
    return books, steps, parts


def not_live_steps() -> dict:
    from ..constants import AI_COLLECT_STEP, AI_FIRE_STEP
    from .steps import NotLive

    return dict.fromkeys((AI_FIRE_STEP, AI_COLLECT_STEP), NotLive())


def config_refused(reason: str) -> dict:
    from ..constants import AI_COLLECT_STEP, AI_FIRE_STEP
    from .steps import ConfigRefused

    return dict.fromkeys((AI_FIRE_STEP, AI_COLLECT_STEP), ConfigRefused(reason))


def build_ai_steps(
    cfg: dict,
    root: Path,
    live,
    parts: dict[str, BookParts],
    processes,
    waiter: Waiter,
    git,
    committer,
    clock: Callable[[], datetime],
    cards: AnalystCards | None = None,
    env=os.environ,
) -> dict:
    """O1's two steps, unwrapped (the daily run's wiring wraps each in `Alerted` with the run's one sender)."""
    from ..ai.history import RepoHistory
    from ..budget.wiring import build_month_meter
    from ..composition import build_record_scanner
    from ..constants import AI_COLLECT_STEP, AI_FIRE_STEP
    from ..desk.pending_commit import PendingCommitter
    from ..desk.timetable import timetable_from_config
    from ..rehearsal.mode import rehearsal
    from .budget import LevelBudgetStop
    from .collect import DecisionCollector
    from .fire import DecisionFirer
    from .no_judge import NoJudge
    from .promote import Promoter
    from .steps import AiCollectStep, AiFireStep, ObserverHandle
    from .terms import decision_terms
    from .timing import DecisionTimingError, decision_timing_from_config

    try:
        timing = decision_timing_from_config(cfg, timetable_from_config(cfg))
    except DecisionTimingError as wrong:
        return config_refused(str(wrong))
    terms, packs, cards = decision_terms(timing), build_day_packs(root), cards or NoAnalystCards()
    rehearsing = lambda: rehearsal() is not None  # noqa: E731 - REH1: a rehearsal never fires (read at each run too)
    triggers = {} if rehearsing() else {book: build_decision_trigger(book, env) for book in ROUTINES}  # judge 651
    marker = PendingCommitter(committer, root, FIRE_LOG_MARKER)  # its own marker, never the run's (E5b's pattern)
    budget, commit = LevelBudgetStop(build_month_meter), marker.commit
    firer = DecisionFirer(root, REGISTRY, triggers, budget, packs, cards, build_record_scanner(), commit, clock, terms)
    deciders = {book: book_parts.decider for book, book_parts in parts.items()}
    pull = lambda: git("pull", "-q", "--no-rebase", "--no-edit", "origin", git.target)  # noqa: E731 - O1 publish branch
    judge_step = (JUDGE_STEP or NoJudge)(root)  # F4 sets JUDGE_STEP when its code lands; until then never a trade
    collector = DecisionCollector(root, RepoHistory(root), REGISTRY, Promoter(root, deciders), packs, cards, pull,
                                  terms, judge_step, clock)  # fmt: skip
    observer = ObserverHandle()
    return {
        AI_FIRE_STEP: AiFireStep(root, firer, timing, live, processes, observer, rehearsing),
        AI_COLLECT_STEP: AiCollectStep(root, collector, timing, live, waiter, clock, observer, rehearsing),
    }
