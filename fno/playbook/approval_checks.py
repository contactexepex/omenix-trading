"""What a strategy version must show to hold an approved status (story D1 criteria 4 and 6). Each check is one rule
behind one interface; the composition root (wiring.py) chooses the list, and the loader and the status change run the
same list, so a file can neither reach nor keep `paper` without passing them."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..constants import PLAYBOOK_FOLDER
from ..research_engine.live_gate import unvalidated
from .documents import strategy_from_text
from .exit_terms import unenforceable_exits
from .fields import PlaybookError
from .history import History
from .live_reports import LiveReports
from .registry import RegistryRow
from .schema import Strategy, require_evidence
from .transitions import PAPER, PAUSED


class LiveFeatureDrift(PlaybookError):
    """A live feature no longer passes its use rule. For a version already on paper this pauses that version only
    (judge 67, story E6); it never refuses the rest of the playbook. A change to paper is still refused."""


class ApprovalCheck(ABC):
    statuses: frozenset  # the statuses this check guards

    @abstractmethod
    def check(self, strategy: Strategy, approval: RegistryRow) -> None:
        """PlaybookError unless `strategy` may hold its status; `approval` is its latest change to paper."""


class EvidenceFilled(ApprovalCheck):
    """Criterion 4: every evidence field filled, the owner's approval date included."""

    statuses = frozenset({PAPER, PAUSED})

    def check(self, strategy: Strategy, approval: RegistryRow) -> None:
        require_evidence(strategy, strategy.status)


class EvidenceCommitted(ApprovalCheck):
    """The evidence is real and was committed before the approval: every evidence file exists in the approval's
    commit, the test results' commit is in its history, and the file's evidence is the one committed there (so it
    cannot be swapped after approval; the evidence sits outside the version's fingerprint)."""

    statuses = frozenset({PAPER, PAUSED})

    def __init__(self, history: History):
        self.history = history

    def check(self, strategy: Strategy, approval: RegistryRow) -> None:
        commit, evidence = approval.evidence_commit, strategy.evidence
        if not self.history.commit_exists(commit):
            raise PlaybookError("registry evidence_commit", f"{commit} is not a commit of this repository")
        for path in evidence.paths:
            if self.history.committed_text(path, commit) is None:
                raise PlaybookError("evidence", f"{path} is not in commit {commit[:10]}")
        if not self.history.is_ancestor(evidence.test_results_commit, commit):
            raise PlaybookError("evidence.test_results_commit", f"is not in the history of {commit[:10]}")
        committed = self.history.committed_text(f"{PLAYBOOK_FOLDER}/{strategy.file_name}", commit)
        if committed is None or strategy_from_text(committed, strategy.file_name).evidence != evidence:
            raise PlaybookError("evidence", f"differs from the evidence committed in {commit[:10]}")


class ExpectedNetSet(ApprovalCheck):
    """Story D2: an approved version needs its frozen expected net per opportunity, the number allocation ranks by."""

    statuses = frozenset({PAPER})

    def check(self, strategy: Strategy, approval: RegistryRow) -> None:
        if strategy.evaluation_plan["expected_net_per_opportunity"] is None:
            raise PlaybookError("evaluation_plan.expected_net_per_opportunity", "must be a number for status paper")


class LiveFeaturesValidated(ApprovalCheck):
    """Criterion 6 (B7's gate): every live feature the conditions use passes the strategy's own frozen use rule."""

    statuses = frozenset({PAPER})

    def __init__(self, reports: LiveReports):
        self.reports = reports

    def check(self, strategy: Strategy, approval: RegistryRow) -> None:
        found = {name: report for name in strategy.live_features if (report := self.reports.report(name))}
        missing = unvalidated(strategy.live_features, found, strategy.live_use_rule)
        if missing:
            raise LiveFeatureDrift(
                "entry_conditions",
                f"live features not validated under the use rule {strategy.live_use_rule}: {missing}",
            )


def run_checks(checks: tuple[ApprovalCheck, ...], strategy: Strategy, approval: RegistryRow | None) -> None:
    for check in checks:
        if strategy.status in check.statuses:
            if approval is None:
                raise PlaybookError("status", f"{strategy.status} without a registered change to paper")
            check.check(strategy, approval)


class ExitsEnforceable(ApprovalCheck):
    """Judge 84: a version may hold `paper` only if code can enforce every exit it states (today the time exit; any
    other exit must read "none"), so no trade is ever opened under a stop nobody applies."""

    statuses = frozenset({PAPER})

    def check(self, strategy: Strategy, approval: RegistryRow) -> None:
        problems = unenforceable_exits(strategy)
        if problems:
            raise PlaybookError("exits", f"code cannot enforce {'; '.join(problems)}: not approvable for paper")
