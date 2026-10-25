"""Composition root of the evaluation protocol (story S1): the repository, its git history and the research ledger
(B4) the freeze registers in, and the protocol definitions by name (S1's evaluation protocol, BR1's breadth protocol,
story BR1a). Swapping any of them changes this file only."""

from __future__ import annotations

from pathlib import Path

from ..config import ROOT
from ..constants import PROTOCOL_BREADTH, PROTOCOL_EVALUATION
from ..playbook.history import PlaybookGit
from .breadth import BREADTH
from .definition import EVALUATION, ProtocolDefinition
from .freeze import ProtocolFreezer

PROTOCOL_DEFINITIONS = {PROTOCOL_EVALUATION: EVALUATION, PROTOCOL_BREADTH: BREADTH}


def protocol_definition(name: str = PROTOCOL_EVALUATION) -> ProtocolDefinition:
    return PROTOCOL_DEFINITIONS[name]


def build_protocol_git(root: Path = ROOT) -> PlaybookGit:
    return PlaybookGit(Path(root))


def build_freezer(root: Path = ROOT, protocol: str = PROTOCOL_EVALUATION) -> ProtocolFreezer:
    return ProtocolFreezer(Path(root), build_protocol_git(root), definition=protocol_definition(protocol))
