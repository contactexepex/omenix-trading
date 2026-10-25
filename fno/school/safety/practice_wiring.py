"""The practice composition of the safety laws (story 7.2, MS-SIM; orchestrator, 22 Oct 2026, design A): the
simulator's root, and only it, builds the laws through here. The size and sell-back checks pass a size nobody measured
and say so (`PRACTICE_SIZE_NOTE`); every other law, the quote's validity and its two sides included, is the live law
unchanged. No live module imports this one (tests pin it)."""

from collections.abc import Mapping

from ...risk.margins import StressedMargin
from ..constants import RoadCode
from ..contracts.snapshot import SlotSnapshot
from ..execution.practice_wiring import PRACTICE
from ..settings import SchoolSettings
from .law_set import SafetyLaws
from .wiring import laws_with


def build_practice_safety_laws(cfg: dict, settings: SchoolSettings, slot: Mapping[RoadCode, SlotSnapshot],
                               margin: StressedMargin) -> SafetyLaws:  # fmt: skip
    return laws_with(cfg, settings, slot, margin, PRACTICE)
