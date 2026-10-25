"""The trial count (story R1, FACTORY_RULES section 5): "trial k of K" in the ledger's order, and the false passes
expected by chance. Every idea is a trial from G0; a measurement (B0) counts in K but is never a test, so it is left
out of the expected false passes (story R1, criterion 10)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class FalsePasses:
    alpha: float
    tests: int  # trials that can pass: K minus the measurements
    measurements: tuple[str, ...]  # trial ids left out

    @property
    def expected(self) -> float:
        return self.tests * self.alpha


class TrialCount:
    def __init__(self, ledger_rows: list[dict]):
        self.ids = [row["trial_id"] for row in ledger_rows]

    @property
    def total(self) -> int:
        return len(self.ids)

    def position(self, trial_id: str) -> int:
        """k, the 1-based place of the trial in the ledger."""
        if trial_id not in self.ids:
            raise KeyError(f"trial {trial_id} is not in the ledger")
        return self.ids.index(trial_id) + 1

    def label(self, trial_id: str) -> str:
        return f"trial {self.position(trial_id)} of {self.total}"

    def false_passes(self, alpha: float, measurement_ids: Iterable[str]) -> FalsePasses:
        left_out = tuple(sorted(set(measurement_ids) & set(self.ids), key=self.ids.index))
        return FalsePasses(alpha, self.total - len(left_out), left_out)
