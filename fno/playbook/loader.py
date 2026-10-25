"""The playbook loader (story D1): every `playbook/<name>-v<n>.yaml`, checked against the registry and the approval
checks. Any refusal stops the whole load: the desk never trades from a playbook with one bad file in it. One exception
(judge 67, story E6): a version on paper whose live feature has drifted is not approved, and is listed as drifted for
its automatic pause; the other versions keep loading. An empty playbook is valid and approves nothing, so Book 1 then
trades nothing."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ..constants import PLAYBOOK_REGISTRY_FILE
from .activation import activation_problem
from .approval_checks import ApprovalCheck, LiveFeatureDrift, run_checks
from .documents import strategy_from_text
from .fields import PlaybookError
from .registry import Registry, RegistryRow
from .rule_checks import RuleCheck
from .schema import Strategy
from .transitions import PAPER, RESEARCH

FILE_PATTERN = "*.yaml"


@dataclass(frozen=True)
class Drift:
    strategy: Strategy
    reason: str


@dataclass(frozen=True)
class Playbook:
    strategies: tuple[Strategy, ...]
    rows: tuple[RegistryRow, ...] = ()  # the registry: every registration and status change, oldest first
    drifted: tuple[Drift, ...] = ()  # paper versions whose live feature drifted: not approved, to be paused

    def _drifted_keys(self) -> set[tuple[str, int]]:
        return {d.strategy.key for d in self.drifted}

    def approved(self) -> tuple[Strategy, ...]:
        """The versions whose file and registry say `paper` now, live features still valid; empty when none."""
        drifted = self._drifted_keys()
        return tuple(s for s in self.strategies if s.status == PAPER and s.key not in drifted)

    def status_on(self, day: date) -> dict[tuple[str, int], str]:
        """Each registered version's status at the start of `day`: its latest change dated before the day (E2's common
        opportunity set and the shadow test use this; a rebuild of the day gives the same answer)."""
        return {row.key: row.status for row in self.rows if row.changed_on < day}

    def status_through(self, day: date) -> dict[tuple[str, int], str]:
        """Each registered version's status after every change dated on or before `day`."""
        return {row.key: row.status for row in self.rows if row.changed_on <= day}

    def approved_on(self, day: date) -> tuple[Strategy, ...]:
        """The versions Book 1 may trade on `day`: `paper` at the start of the day AND still `paper` after every change
        dated that day (judge 74, risk manager's rule). An approval waits for the next session; a pause or retirement
        stops new entries at once. Both read the registry's dates only, so a rebuild of the day gives the same set;
        on the live day no later row exists, so "through the day" is "now". A drifted version is never approved (judge
        67): before E6 its drift refused the whole load, so excluding it here is no less safe on a rebuild."""
        start, through, drifted = self.status_on(day), self.status_through(day), self._drifted_keys()
        return tuple(
            s
            for s in self.strategies
            if start.get(s.key) == PAPER and through.get(s.key) == PAPER and s.key not in drifted
        )

    def shadow_on(self, day: date) -> tuple[Strategy, ...]:
        """Research candidates registered (frozen) before `day`: forward-tested in shadow (owner, 14 Oct 2026), never
        in a book's account. An unregistered candidate is not frozen, so it is not tested."""
        status = self.status_on(day)
        return tuple(s for s in self.strategies if status.get(s.key) == RESEARCH)

    def get(self, name: str, version: int) -> Strategy:
        found = [s for s in self.strategies if s.key == (name, version)]
        if not found:
            raise PlaybookError(f"{name} v{version}", "no such playbook file")
        return found[0]


class PlaybookLoader:
    def __init__(self, folder: Path, registry: Registry, checks: Sequence[ApprovalCheck],
                 rule_checks: Sequence[RuleCheck] = ()):  # fmt: skip
        self.folder, self.registry, self.checks, self.rule_checks = folder, registry, tuple(checks), tuple(rule_checks)

    def load(self) -> Playbook:
        strategies = self._read_files()
        rows, drifted = self.registry.rows(), []
        for strategy in strategies:
            history = [row for row in rows if row.key == strategy.key]
            try:
                self.check_against_history(strategy, history)
            except LiveFeatureDrift as drift:
                if strategy.status != PAPER:
                    raise
                drifted.append(Drift(strategy, str(drift)))
        self._require_files_for(rows, {s.key for s in strategies})
        return Playbook(tuple(strategies), tuple(rows), tuple(drifted))

    def check_against_history(self, strategy: Strategy, history: Sequence[RegistryRow]) -> None:
        """The file matches its registered fingerprint and latest status, and passes the checks for that status."""
        where = strategy.file_name
        latest = history[-1] if history else None
        if latest and latest.sha256 != strategy.parameters_sha256:
            raise PlaybookError(
                f"{where}: rule", "differs from the registered version: a changed rule is a new version"
            )
        registered = latest.status if latest else RESEARCH
        if strategy.status != registered:
            raise PlaybookError(f"{where}: status", f"is {strategy.status} but the registry says {registered}")
        approval = next((row for row in reversed(history) if row.status == PAPER), None)
        blocked = activation_problem(strategy, registered=bool(history))
        if blocked:
            raise PlaybookError(f"{where}: structure", blocked)
        try:
            for rule_check in self.rule_checks:
                rule_check.check(strategy)
            run_checks(self.checks, strategy, approval)
        except PlaybookError as refused:
            raise type(refused)(f"{where}: {refused.field}", refused.reason) from None

    def _read_files(self) -> list[Strategy]:
        paths = sorted(self.folder.glob(FILE_PATTERN)) if self.folder.is_dir() else []
        strategies = [strategy_from_text(path.read_text(encoding="utf-8"), path.name) for path in paths]
        seen: dict[tuple[str, int], str] = {}
        for path, strategy in zip(paths, strategies, strict=True):
            if strategy.key in seen:
                raise PlaybookError(f"{seen[strategy.key]} and {path.name}", "same name and version in two files")
            seen[strategy.key] = path.name
        for path, strategy in zip(paths, strategies, strict=True):
            if path.name != strategy.file_name:
                raise PlaybookError(path.name, f"must be named {strategy.file_name} (its name and version)")
        return strategies

    @staticmethod
    def _require_files_for(rows: Sequence[RegistryRow], present: set[tuple[str, int]]) -> None:
        for row in rows:
            if row.key not in present:
                raise PlaybookError(f"{row.name} v{row.version}", "registered but its playbook file is missing")


def registry_path(folder: Path) -> Path:
    return folder / PLAYBOOK_REGISTRY_FILE
