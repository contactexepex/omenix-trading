"""What makes one pre-registered protocol (story BR1a): its file, its required items, its freeze record's path and
wording, its ledger row, and whether the real-money gate (story RM1) is frozen with it. The freezer and the checks read
everything protocol-specific from here, so a second protocol is one new definition passed in by the composition root
(`wiring.py`). S1's evaluation protocol is the default, so S1's behaviour, file names and records are unchanged."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .protocol import PROTOCOL_FILE, REQUIRED_ITEMS


@dataclass(frozen=True)
class ProtocolDefinition:
    protocol_file: str
    required_items: Mapping[str, str]
    freeze_template: str  # with {version}
    record_title: str
    record_rule: str  # who says a changed target is a new version
    ledger_description: str  # with {version}
    ledger_experiment: str  # with {version}
    requires_gate: bool  # the real-money gate is listed, complete and decided before the freeze

    def freeze_path(self, version: int) -> str:
        return self.freeze_template.format(version=version)


EVALUATION = ProtocolDefinition(
    protocol_file=PROTOCOL_FILE,
    required_items=REQUIRED_ITEMS,
    freeze_template="research/evaluation/FREEZE_v{version}.md",
    record_title="Evaluation protocol freeze record",
    record_rule="story S1, criterion 3",
    ledger_description="Evaluation protocol v{version}: the three books' comparison rules (story S1)",
    ledger_experiment="evaluation-protocol-v{version}",
    requires_gate=True,
)
