"""Composition root of Book 3's strategy registry (story D5): the repository folder, its git history, the research
ledger (B4) every registered strategy enters, and the IST clock that dates a registration. Swapping any of them
changes this file only."""

from __future__ import annotations

from pathlib import Path

from ..config import ROOT
from ..models import now_ist
from ..research_engine.ledger import Git, Ledger
from .registry import StrategyRegistry


def build_strategy_registry(root: Path = ROOT) -> StrategyRegistry:
    return StrategyRegistry(Path(root), Git(Path(root)), Ledger(Path(root)), lambda: now_ist().date())
