"""Composition root of the scorecards and pause rules (story E6): the accounts read (the three books and every shadow
version's account), the playbook and its status changer (D1), the alert sender, the charges table, and the execution
snapshots the half-spread reads its touches from (story E2b)."""

from __future__ import annotations

from pathlib import Path

from ..alerts.sender import AlertSender
from ..books.account import PaperAccount
from ..composition import build_alert_sender
from ..config import ROOT
from ..desk.private_files import paper_accounts
from ..desk.records import DeskRecords
from ..desk.wiring import build_execution_snapshots
from ..playbook.wiring import build_playbook_loader, build_status_changer
from ..storage.wiring import QUOTES_FOLDER
from .pauses import AutoPauser
from .review import review_terms
from .run import ScorecardRun


def build_scorecard_run(cfg: dict, root: Path = ROOT, alerts: AlertSender | None = None) -> ScorecardRun:
    """`alerts`: the daily run's one sender (story O1), so an unsent pause alert is printed for the routine."""
    pauser = AutoPauser(build_status_changer(root), alerts or build_alert_sender())
    return ScorecardRun(
        lambda: paper_accounts(root), lambda name: DeskRecords(PaperAccount(root, name)), build_playbook_loader(root),
        pauser, cfg["charges"], review_terms(cfg), build_execution_snapshots(root / QUOTES_FOLDER.relative_to(ROOT)),
    )  # fmt: skip
