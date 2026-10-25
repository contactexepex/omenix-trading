"""The shadows the stop rule's Test B counts (story R1c; `fno/budget/stop_rule_tracker.py`, input "shadow strategies
registered in the ledger with pass mark and minimum useful net"): every G4 `registered` row of the gate log. A
measurement is never registered (G4 refuses it by its playbook `edge_family`), so none is ever listed. R3's closed
trades join this list in the stop rule's `money_test`; R1 never reads closed trades for Test B."""

from __future__ import annotations

from dataclasses import dataclass

from .constants import Gate
from .gate_log import GateLog, figures


@dataclass(frozen=True)
class RegisteredShadow:
    trial_id: str
    version: str  # `<name>-v<n>`; its account is `shadow:<name>-v<n>`
    sample: int  # the frozen sample: completed positions
    pass_level: float  # one-sided, its question's alpha
    minimum_useful_net: float  # rupees a trade
    question_id: str


class RegisteredShadows:
    def __init__(self, gates: GateLog):
        self.gates = gates

    def all(self) -> list[RegisteredShadow]:
        self.gates.require_append_only()
        return [self._shadow(row.trial_id, figures(row)) for row in self.gates.of_gate(Gate.REGISTRATION)]

    @staticmethod
    def _shadow(trial_id: str, numbers: dict[str, str]) -> RegisteredShadow:
        return RegisteredShadow(trial_id, numbers["version"], int(numbers["sample"]), float(numbers["pass_level"]),
                                float(numbers["min_net"]), numbers["question"])  # fmt: skip
