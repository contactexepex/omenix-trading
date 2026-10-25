"""What Book 1's committed decision records fix for its trades (story E5, judge 84): each trade's terms (structure,
width, lots), for C2's view of the book, and its time exit, fixed at the decision. The exit day comes from the run's
own inputs, never today's playbook folder: the version file as the run read it (`inputs.json`), and the trade's expiry
from its opportunity ID, through D2's `OpportunityFinder.exit_day`. So no later edit to a version file, and no
unrelated file that no longer parses, can stop or move an open trade's exit.

Only the book's filled trades count, each from the run that opened it (story D3b, `opening_runs`). A record with the
same trade ID in any other run, a correction included, never changes the trade: it is reported, as `other_runs`.
A trade with no opening run (its run log missing or mismatched) has no terms and no exit here, with the reason."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ..constants import SHADOW_PREFIX
from ..playbook.decision_store import INPUTS_FILE, DecisionStore
from ..playbook.documents import strategy_from_text
from ..playbook.opportunities import SHADOW, OpportunityFinder
from ..playbook.run_order import run_counter
from ..risk.inputs import TradeTerms
from .opening_runs import opening_runs

TRADE = "trade"
NOT_IN_RUN = "its opening run {run} holds no chosen record of it"


@dataclass(frozen=True)
class DecidedTrade:
    trade_id: str
    version: str  # "<name>-v<n>"
    expiry: date
    terms: TradeTerms
    run: Path


@dataclass(frozen=True)
class BookTrades:
    trades: Mapping[str, DecidedTrade]  # the book's filled trades, each from its opening run
    problems: Mapping[str, str]  # filled trades with no opening record, and why
    other_runs: Mapping[str, tuple[str, ...]]  # trade ID -> other runs whose records name it (shown, never used)


@dataclass(frozen=True)
class DecidedExits:
    exits: Mapping[str, tuple[date, str]]  # trade ID -> (exit day, version)
    problems: Mapping[str, str]
    other_runs: Mapping[str, tuple[str, ...]]


def opening_trades(root: Path, book: str, decider: str | None = None) -> BookTrades:
    """A book reads only its own records; a shadow account (`decider` Book 1) only records of mode `shadow` (R3)."""
    openings = opening_runs(root, book, decider)
    chosen: dict[str, list[DecidedTrade]] = {}
    shadow = book.startswith(SHADOW_PREFIX)
    for record_path in _record_files(DecisionStore(root, decider or book)):
        trade = _chosen(record_path, shadow)
        if trade is not None:
            chosen.setdefault(trade.trade_id, []).append(trade)
    trades, problems, others = {}, dict(openings.problems), {}
    for trade_id, run in openings.runs.items():
        own = [t for t in chosen.get(trade_id, ()) if t.run == run]
        if own:
            trades[trade_id] = own[0]
        else:
            problems[trade_id] = NOT_IN_RUN.format(run=run.name)
    for trade_id in (*openings.runs, *openings.problems):
        opening = openings.runs.get(trade_id)
        elsewhere = sorted({t.run for t in chosen.get(trade_id, ()) if t.run != opening}, key=_day_and_counter)
        if elsewhere:
            others[trade_id] = tuple(r.name for r in elsewhere)
    return BookTrades(trades, problems, others)


def recorded_terms(root: Path, book: str, decider: str | None = None) -> dict[str, TradeTerms]:
    """Each filled trade's structure, width and lots, by trade ID, from its opening run."""
    return {t.trade_id: t.terms for t in opening_trades(root, book, decider).trades.values()}


def decided_exit_days(root: Path, book: str, finder: OpportunityFinder) -> DecidedExits:
    """Each filled trade's time exit as fixed at its opening decision, with the trades that have none and why."""
    found = opening_trades(root, book)
    exits, files = {}, {}
    for trade in found.trades.values():
        if trade.run not in files:
            files[trade.run] = json.loads((trade.run / INPUTS_FILE).read_text(encoding="utf-8"))["playbook"]["files"]
        name = f"{trade.version}.yaml"
        strategy = strategy_from_text(files[trade.run][name], name)
        exits[trade.trade_id] = (finder.exit_day(strategy, trade.expiry), trade.version)
    return DecidedExits(exits, found.problems, found.other_runs)


def _record_files(store: DecisionStore) -> list[Path]:
    """Every record file of the book's runs, through the store's own listing, so a hidden temporary folder left by a
    crashed write is never read."""
    return [path for run in store.every_run() for path in run.glob("*.json")]


def _day_and_counter(run: Path) -> tuple[str, int]:
    """Only to list other runs for an alert, by day then run counter (never by name): nothing is chosen by it."""
    return run.parent.name, run_counter(run)


def _chosen(record_path: Path, shadow: bool) -> DecidedTrade | None:
    """A book's reader never takes a shadow's record, and a shadow's reader only those (judge 208: the isolation must
    not rest on the trade ID's `shadow-` prefix alone)."""
    if record_path.name == INPUTS_FILE:
        return None
    record = json.loads(record_path.read_text(encoding="utf-8"))
    trade = record.get("structure")
    if record.get("chosen_action") != TRADE or not trade or (record.get("mode") == SHADOW) != shadow:
        return None
    version, _, expiry = record["opportunity_id"].rpartition(":")
    terms = TradeTerms(trade["structure"], trade["width"], trade["lots"])
    return DecidedTrade(trade["trade_id"], version, date.fromisoformat(expiry), terms, record_path.parent)
