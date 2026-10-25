"""Book 3's strategy registry (story D5; design 12.3; F6): every strategy Book 3 invents is registered, with its full
spec in D1's playbook format and the spec's hash, before its first trade. `book3/strategies/registry.csv` is
append-only, one row per strategy; `book3/strategies/<strategy_id>.yaml` holds the spec. A material change is a new
`strategy_id` naming what it supersedes. `register` sets `proposed_on` from the clock, never from the spec (judge 207),
and enters the strategy into the research ledger's Book 3 trial family (B4), so a variant chosen after the market data
still counts as a trial (ChatGPT review 130, point 2). A row cannot name the commit that adds it, so the registering
commit is read from git history: a decision may use a strategy only when its row and spec are committed at the commit
the decision is checked against, and were proposed on an earlier session (no same-day invent-and-trade)."""

from __future__ import annotations

import csv
import io
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from ..constants import BOOK3_FOLDER
from ..playbook.documents import strategy_from_text
from ..research_engine.ledger import Git, Ledger
from .constitution import Constitution
from .spec_rules import constitution_problems

STRATEGIES = f"{BOOK3_FOLDER}/strategies"
REGISTRY_FILE = f"{STRATEGIES}/registry.csv"
COLUMNS = ("strategy_id", "spec_sha256", "proposed_on", "model", "prompt_version", "role_set_version",
           "new_or_reused", "supersedes")  # fmt: skip
NEW_OR_REUSED = ("new", "reused")
TRIAL_FAMILY = "book3_ai strategies"  # the research ledger's experiment for every Book 3 strategy


class RegistrationRefused(ValueError):
    pass


class NotRegistered(RuntimeError):
    pass


@dataclass(frozen=True)
class Provenance:
    model: str
    prompt_version: str
    role_set_version: str
    new_or_reused: str
    supersedes: str = ""


def spec_path(strategy_id: str) -> str:
    return f"{STRATEGIES}/{strategy_id}.yaml"


def parse_registry(text: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(text))
    if text and tuple(reader.fieldnames or ()) != COLUMNS:
        raise ValueError(f"{REGISTRY_FILE} columns must be {COLUMNS}")
    return list(reader)


def _render(rows: list[dict]) -> str:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


class StrategyRegistry:
    def __init__(self, root: Path, git: Git, ledger: Ledger, today: Callable[[], date]):
        self.root, self.git, self.ledger, self.today = Path(root), git, ledger, today

    def rows(self) -> list[dict]:
        path = self.root / REGISTRY_FILE
        return parse_registry(path.read_text(encoding="utf-8")) if path.is_file() else []

    def register(self, raw_spec: str, provenance: Provenance, constitution: Constitution) -> dict:
        """Writes the spec and appends its row (commit both, and the ledger, together)."""
        spec = strategy_from_text(raw_spec, "the proposed spec")
        strategy_id, rows = f"{spec.name}-v{spec.version}", self.rows()
        problems = constitution_problems(spec, constitution)
        if problems:
            raise RegistrationRefused(f"{strategy_id}: " + "; ".join(problems))
        known = {r["strategy_id"] for r in rows}
        if strategy_id in known or (self.root / spec_path(strategy_id)).exists():
            raise RegistrationRefused(f"{strategy_id} is already registered: a change is a new strategy_id")
        unknown_parent = bool(provenance.supersedes) and provenance.supersedes not in known
        if provenance.new_or_reused not in NEW_OR_REUSED or unknown_parent:
            raise RegistrationRefused(f"{strategy_id}: new_or_reused must be {NEW_OR_REUSED}; supersedes a known id")
        row = {"strategy_id": strategy_id, "spec_sha256": spec.parameters_sha256,
               "proposed_on": self.today().isoformat(), **asdict(provenance)}  # fmt: skip
        (self.root / STRATEGIES).mkdir(parents=True, exist_ok=True)
        (self.root / spec_path(strategy_id)).write_text(raw_spec, encoding="utf-8")
        (self.root / REGISTRY_FILE).write_text(_render([*rows, row]), encoding="utf-8")
        self.ledger.register(f"book3:{strategy_id}", TRIAL_FAMILY, f"Book 3 strategy {strategy_id}", "prospective",
                             True, spec_path(strategy_id), self.today())  # fmt: skip
        return row

    def require_registered(self, strategy_id: str, decision_day: date, at_commit: str):
        """The registered spec, or NotRegistered: its row and spec must be committed at `at_commit`, proposed before
        the decision day, unchanged since, and the registry never edited (criteria 1, 2 and 5)."""
        if self.git.is_shallow():
            raise NotRegistered(
                "a shallow clone hides the registry's history: fetch it in full (git fetch --unshallow)"
            )
        committed = self.git.committed_text(REGISTRY_FILE, at_commit)
        row = next((r for r in parse_registry(committed or "") if r["strategy_id"] == strategy_id), None)
        if row is None:
            raise NotRegistered(f"{strategy_id}: not registered in a commit before the decision")
        if date.fromisoformat(row["proposed_on"]) >= decision_day:
            raise NotRegistered(f"{strategy_id}: proposed on {row['proposed_on']}, not before {decision_day}")
        text = self.git.committed_text(spec_path(strategy_id), at_commit)
        current = self.root / spec_path(strategy_id)
        on_disk = current.read_text(encoding="utf-8") if current.is_file() else None
        spec = strategy_from_text(text, spec_path(strategy_id)) if text else None
        if spec is None or on_disk != text or spec.parameters_sha256 != row["spec_sha256"]:
            raise NotRegistered(f"{strategy_id}: the spec differs from the one registered (hash)")
        if len(self.git.commits_touching(spec_path(strategy_id))) > 1:  # even an edit that keeps the rule's hash
            raise NotRegistered(f"{strategy_id}: the spec file differs from the one registered (edited after it)")
        edited = self.edited_rows(at_commit)
        if edited:
            raise NotRegistered(f"the registry was edited, not appended to: {edited}")
        return spec

    def edited_rows(self, revision: str = "HEAD") -> list[str]:
        """Rows that a commit changed or removed from any of its parents' registries (criterion 5). Each commit is read
        against each parent, so two registrations on parallel lines of history, merged with both rows kept, are two
        appends; a merge that drops or edits either side's row is an edit."""
        edited = []
        for commit, parents in self.git.changes_with_parents(REGISTRY_FILE, revision):
            newer = self._registry_at(commit)
            for parent in parents:
                edited += [r["strategy_id"] for r in self._registry_at(parent) if r not in newer]
        return list(dict.fromkeys(edited))

    def _registry_at(self, commit: str) -> list[dict]:
        return parse_registry(self.git.committed_text(REGISTRY_FILE, commit) or "")
