"""One book's decision run and its replay (story D3). `DecisionRun.decide` evaluates the day with D2 while recording
every input D2 reads, builds the records, and writes them atomically; `replay` re-runs D2 on a stored run's inputs and
lists every field that differs from the stored records (criterion 2: the same decision, the same rejected
alternatives, every risk and validity reason)."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import date
from pathlib import Path

from ..desk.pack_items import canonical_json, sha256_hex
from ..risk.inputs import Market, RiskBook
from .allocation import StrategyTradeCounts
from .code_tree import CodeTree
from .decision_codec import book_to_json, market_to_json
from .decision_inputs import DayInputs, PlaybookSnapshot, RecordingCounts, RecordingFeatures, RecordingShadowBooks
from .decision_record import NO_TRADE_ID, RecordBuilder, run_context_of
from .decision_store import INPUTS_FILE, DecisionStore, record_file
from .decision_validity import TradeValidator, validate_chosen
from .evaluate import LiveFeatureValues, RuleEvaluator
from .loader import Playbook
from .shadow import ShadowBooks

RUN_CONTEXT = ("code_commit", "config_sha256", "version_id", "common_pack_sha256", "private_pack_sha256",
               "authority_check", "strategy_id", "strategy_spec_sha256", "model_served", "session_id", "judge",
               "owner_override", "forecasts")  # fmt: skip


def playbook_digest(playbook: Playbook, day: date) -> str:
    """Book 1's served playbook: the rule fingerprints of the versions it may trade on the day."""
    keys = sorted(f"{s.name}-v{s.version}:{s.parameters_sha256}" for s in playbook.approved_on(day))
    return hashlib.sha256("\n".join(keys).encode("utf-8")).hexdigest()


def file_hashes(snapshot: PlaybookSnapshot) -> dict[str, str]:
    return {name: sha256_hex(text.encode("utf-8")) for name, text in snapshot.files.items()}


class DecisionRun:
    def __init__(self, evaluator: RuleEvaluator, store: DecisionStore, validator: TradeValidator | None = None):
        self.evaluator, self.store, self.validator = evaluator, store, validator

    def decide(
        self, day: date, snapshot: PlaybookSnapshot, market: Market, features: LiveFeatureValues, book: RiskBook,
        counts: StrategyTradeCounts, shadow: ShadowBooks, context: Mapping[str, object],
    ) -> Path:  # fmt: skip
        """`context` gives the run's hashes and links (RUN_CONTEXT); `served` is computed here, never passed in."""
        playbook = snapshot.playbook()
        evaluation, data = self._evaluate(day, snapshot, market, features, book, counts, shadow)
        served = {"playbook": playbook_digest(playbook, day), "config": str(context["config_sha256"])}
        run_context = {**{k: context.get(k) for k in RUN_CONTEXT}, "inputs_sha256": sha256_hex(data),
                       "registry_commit": snapshot.commit, "served": served}  # fmt: skip
        run_id = self.store.next_run_id(day)
        validity = validate_chosen(evaluation, self.validator, market, playbook, book)
        records = RecordBuilder(book.name, run_id, run_context, validity).build(evaluation, file_hashes(snapshot))
        run = self.store.write(day, run_id, data, records)
        if self.validator is not None:  # only after the write: a refused duplicate run logs nothing (judge 84, D)
            self.validator.log_failures(day, validity)
        return run

    def inputs(
        self, day: date, snapshot: PlaybookSnapshot, market: Market, features: LiveFeatureValues, book: RiskBook,
        counts: StrategyTradeCounts, shadow: ShadowBooks,
    ) -> bytes:  # fmt: skip
        """The `inputs.json` bytes a decision would record now; nothing is written and nothing decided (story E5b)."""
        return self._evaluate(day, snapshot, market, features, book, counts, shadow)[1]

    def _evaluate(self, day, snapshot, market, features, book, counts, shadow) -> tuple:
        """D2's evaluation while recording every input it reads, and those inputs as `inputs.json` bytes."""
        seen_features, seen_counts, seen_shadow = (
            RecordingFeatures(features),
            RecordingCounts(counts),
            RecordingShadowBooks(shadow),
        )
        playbook = snapshot.playbook()
        evaluation = self.evaluator.evaluate(day, playbook, market, seen_features, book, seen_counts, seen_shadow)
        inputs = DayInputs(day, snapshot, market_to_json(market), seen_features.seen, book_to_json(book),
                           seen_counts.seen, seen_shadow.to_json())  # fmt: skip
        return evaluation, canonical_json(inputs.to_json())


class ReplayRefused(ValueError):
    """The running code is not the code the run was decided with: a replay here would prove nothing."""


def replay(
    run: Path, evaluator: RuleEvaluator, code: CodeTree, todays_code: bool = False,
    validator: TradeValidator | None = None,
) -> list[str]:  # fmt: skip
    """Every difference between the stored records and a fresh D2 evaluation (and C4 check, with `validator`) of the
    stored inputs; empty if equal. Refused unless the running code is the record's `code_commit`; `todays_code` runs
    anyway and says so first."""
    data = (run / INPUTS_FILE).read_bytes()
    day_record = json.loads((run / record_file(NO_TRADE_ID)).read_text(encoding="utf-8"))
    commit = day_record["header"]["code_commit"]
    note = []
    if not code.matches(commit):
        if not todays_code:
            raise ReplayRefused(
                f"{run.name} was decided with code {commit}; the running fno/ and config.yaml differ. Replay in a "
                f"worktree of that commit (git worktree add <dir> {commit})"
            )
        note = [f"NOTE: compared with today's code, not the recorded commit {commit}: not a reproduction"]
    if day_record["header"]["inputs_sha256"] != sha256_hex(data):
        return [*note, f"{INPUTS_FILE}: its SHA-256 differs from the one the records name"]
    inputs = DayInputs.from_json(json.loads(data))
    arguments = inputs.replay_arguments()
    evaluation = evaluator.evaluate(*arguments)
    _, playbook, market, _, book = arguments[:5]
    validity = validate_chosen(evaluation, validator, market, playbook, book)
    context = run_context_of(day_record)
    rebuilt = RecordBuilder(day_record["book"], day_record["run_id"], context, validity).build(
        evaluation, file_hashes(inputs.playbook)
    )
    stored = {p.name: json.loads(p.read_text(encoding="utf-8")) for p in run.glob("*.json") if p.name != INPUTS_FILE}
    fresh = {record_file(r["opportunity_id"], r.get("mode")): json.loads(canonical_json(r)) for r in rebuilt}
    differences = [f"{name}: missing in the replay" for name in sorted(set(stored) - set(fresh))]
    differences += [f"{name}: not in the stored run" for name in sorted(set(fresh) - set(stored))]
    for name in sorted(set(stored) & set(fresh)):
        differences += [
            f"{name}: {key} differs" for key in sorted(stored[name]) if stored[name][key] != fresh[name].get(key)
        ]
    return note + differences
