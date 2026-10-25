"""C4's completed pass as E3 reads it (judge 83 ruling): the fill reads the committed D3 record's `validity.c4`, which
C4 wrote inside the decision run against the decision's own capture. It never runs C4 again at the 15:15 execution
capture: those quotes differ from the decision's, so every leg's price check would fail by design.

The order's `decision_id` names its D3 record (the record's opportunity ID; E5 and the AI books set it so). The run's
files must still match the `records.sha256` committed with them, and the record must hold a C4 report that passed,
with its checks; a missing, empty, failed or edited one is never filled."""

from __future__ import annotations

import json

from ..playbook.decision_store import DecisionStore, record_file
from .daily_ports import CommittedDecision, ValidityGate
from .entries import EntryOrder

NO_RUN = "the decision names no D3 run folder: no recorded C4 pass can be read"
NO_RECORD = "{run}: no D3 record {name} for this order"
EDITED = "{run}: files changed after they were committed: {files}"
NOT_RUN = "{name}: no completed C4 pass recorded (validity.c4 is {c4})"
FAILED = "{name}: C4 failed: {checks}"


class RecordedC4Pass(ValidityGate):
    def problems(self, decision: CommittedDecision, order: EntryOrder) -> list[str]:
        if decision.run is None:
            return [NO_RUN]
        name = record_file(order.decision_id)
        path = decision.run / name
        if not path.is_file():
            return [NO_RECORD.format(run=decision.run_id, name=name)]
        edited = DecisionStore.edited(decision.run)
        if edited:
            return [EDITED.format(run=decision.run_id, files=", ".join(edited))]
        c4 = (json.loads(path.read_text(encoding="utf-8")).get("validity") or {}).get("c4")
        if not isinstance(c4, dict) or not isinstance(c4.get("ok"), bool) or not c4.get("checks"):
            return [NOT_RUN.format(name=name, c4=json.dumps(c4))]
        if not c4["ok"]:
            failed = [check.get("check", "?") for check in c4["checks"] if not check.get("ok")]
            return [FAILED.format(name=name, checks=", ".join(failed) or "no check named")]
        return []
