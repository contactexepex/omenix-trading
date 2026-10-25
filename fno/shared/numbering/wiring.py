"""Composition root for number claims (story O12): the claimer on this repository's `origin/main`."""

from __future__ import annotations

from pathlib import Path

from fno.shared.numbering.claim import NumberClaimer
from fno.shared.numbering.git_main import GitMain


def build_number_claimer(repository: Path) -> NumberClaimer:
    return NumberClaimer(GitMain(repository))
