"""G4, the freeze (story R1c): a planned idea's frozen protocol commit goes into its ledger row (B4) and the gate log
gets its `registered` row with the frozen sample, pass level, minimum useful net, question and playbook version.

Only an idea whose last gate is G3 is frozen, so a `screened_out` idea never gets a registered shadow (R3's step 3). A
counterexample study (FACTORY_RULES section 3, rule 2) is frozen by hand until a real one exists (R1 Known limits). A
measurement version is refused by its playbook file's `edge_family` (`is_measurement`), the one source R3 keeps."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Protocol

from ..desk.trade_counts import version_tag
from ..playbook.fields import PlaybookError
from ..playbook.measurement import is_measurement
from ..playbook.schema import Strategy
from ..research_engine.ledger import LEDGER_FILE, Ledger, read_ledger, write_ledger
from .card import IdeaCard
from .constants import Gate, Outcome
from .gate_log import GateRow, figures
from .gate_order import GateOrder, GateStepError
from .inputs import plan_inputs, registration_inputs
from .questions import Questions


class PlaybookVersions(Protocol):
    def get(self, name: str, version: int) -> Strategy: ...


class FactoryFreeze:
    def __init__(self, order: GateOrder, ledger: Ledger, questions: Questions, versions: PlaybookVersions):
        self.order, self.ledger, self.questions, self.versions = order, ledger, questions, versions

    def freeze(self, card: IdeaCard, today: date) -> GateRow:
        self.order.ready(card, Gate.SAMPLE_PLAN, (Outcome.PLANNED, Outcome.EXPLORATORY_SHADOW), staged=(LEDGER_FILE,))
        question, inputs, level = self.questions.get(card.question), registration_inputs(card), plan_inputs(card)
        if question.alpha != level.pass_level:
            raise GateStepError(f"{card.path}: pass level {level.pass_level:g} is not question "
                                f"'{question.question_id}''s alpha {question.alpha:g}")  # fmt: skip
        tag = version_tag(inputs.playbook_name, inputs.playbook_version)
        if is_measurement(self._strategy(inputs.playbook_name, inputs.playbook_version, tag)):
            raise GateStepError(f"{tag} is a measurement (edge_family): never frozen as a shadow to judge")
        sample = figures(self.order.row(card.trial_id, Gate.SAMPLE_PLAN))["n"]
        numbers = (f"version={tag};sample={sample};pass_level={level.pass_level:g};"
                   f"min_net={inputs.minimum_useful_net:g};question={question.question_id}")  # fmt: skip
        commit, write_ledger_row = self._protocol_commit(card)
        registered, append = self.order.prepare(card, Gate.REGISTRATION, Outcome.REGISTERED, today, numbers, commit)
        write_ledger_row()  # every git read is done: a failed one leaves nothing half written
        append()
        return registered

    def _strategy(self, name: str, version: int, tag: str) -> Strategy:
        try:
            return self.versions.get(name, version)
        except PlaybookError as missing:
            raise GateStepError(f"playbook version {tag} cannot be read: {missing}") from missing

    def _protocol_commit(self, card: IdeaCard) -> tuple[str, Callable[[], None]]:
        """The frozen protocol commit and the write that records it in the ledger row. The card, committed and
        unchanged at HEAD, is the frozen protocol (B4's require_registered checks it). A row whose commit is already
        set is a freeze that stopped before its gate row: it is completed at that commit, never refrozen."""
        rows = self.ledger.rows()
        row = next((r for r in rows if r["trial_id"] == card.trial_id), None)
        if row is None or row["protocol_path"] != card.path:
            raise GateStepError(f"trial {card.trial_id}'s ledger row does not name {card.path} as its protocol")
        frozen, git = row["protocol_commit"], self.order.git
        if frozen:
            if not (git.is_ancestor(frozen, git.head()) and git.unchanged_since(frozen, card.path)):
                raise GateStepError(f"trial {card.trial_id} is already frozen at {frozen[:10]}, which is not "
                                    f"{card.path} as it is now")  # fmt: skip
            return frozen, lambda: None
        head = git.head()
        updated = [r | {"protocol_commit": head} if r is row else r for r in rows]
        text = write_ledger(read_ledger(write_ledger(updated)))  # validated before any write
        return head, lambda: self.ledger.file.write_text(text)
