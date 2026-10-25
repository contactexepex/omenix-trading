"""Composition root of the instructor's review sources (story MS-INS, part e follow-up, after MS-P1j's wiring): the
fired entries that never filled, from MS-P1j's `build_unfilled_entries`, and f's three counts, from the counts file
each session's run commits (MS-P1j's `SealedDayInputs`). Apart from `wiring.py` because MS-P1j's composition root
imports that one: this root imports MS-P1j's, so only the command's entry point imports it. Read-only."""

from pathlib import Path

from ...config import ROOT
from ..dashcam.wiring import build_dashcam
from ..fleet.report_inputs import SealedDayInputs
from ..wiring import build_unfilled_entries
from .outputs.review import ReviewSources


def build_review_sources(config: dict, root: Path = ROOT) -> ReviewSources:
    counts = SealedDayInputs(build_dashcam(), root, roles={})  # only its committed counts file is read
    return ReviewSources(build_unfilled_entries(config, root), counts)
