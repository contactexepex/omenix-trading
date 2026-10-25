"""The calibrated thresholds a look uses (protocol v4 5.3 and 5.5; story G8), computed at the look for the member's
actual n by the frozen tools in `tools/`, never by G8: V1 and V2 `v4_claim_thresholds.claim_threshold` and
`v4_futility_study.futility_threshold`; V6a and V6b `v4_brier_bands.operative_thresholds` for the window's band. Each
call takes seconds to a minute (17 s, 7 s and 56 s measured at n = 125)."""

from __future__ import annotations

import importlib
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from ...forecast_v4.terms import LOOK_ERROR_RATE, LOOK_SETTLE_DATE, LOOK_STOP_REVIEW, POINT_QUESTIONS

TOOL_LOOK = {LOOK_STOP_REVIEW: "look 1", LOOK_SETTLE_DATE: "look 2"}  # the Brier tool's names for the two looks


@dataclass(frozen=True)
class Thresholds:
    claim: float  # the batch-means t p-value at or below which a claim is significant
    futility: float  # the futility p-value at or below which a member is futile


class ThresholdSource(ABC):
    @abstractmethod
    def thresholds(self, question: str, look: str, claim_n: int, futility_n: int, band) -> Thresholds:
        """`claim_n`: the scored set's size; `futility_n`: the gate set's; `band`: the window's 2%-day band."""


class FrozenToolThresholds(ThresholdSource):
    def __init__(self, tools_folder: Path):
        self.tools_folder = Path(tools_folder)

    def _tool(self, name: str):
        if str(self.tools_folder) not in sys.path:
            sys.path.insert(0, str(self.tools_folder))
        return importlib.import_module(name)

    def thresholds(self, question: str, look: str, claim_n: int, futility_n: int, band) -> Thresholds:
        if question in POINT_QUESTIONS:  # the tool divides the look's rate by 15 itself
            claim = self._tool("v4_claim_thresholds").claim_threshold(question, claim_n, LOOK_ERROR_RATE[look])
            return Thresholds(claim, self._tool("v4_futility_study").futility_threshold(question, futility_n))
        found = self._tool("v4_brier_bands").operative_thresholds(question, claim_n, band)
        return Thresholds(found["claim"][TOOL_LOOK[look]], found["futility"])
