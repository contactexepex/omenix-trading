"""Composition root of the playbook (story D1): the one place its concrete parts are chosen and joined."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from ..config import ROOT
from ..constants import PLAYBOOK_FOLDER
from ..storage.wiring import LIVE_VALIDATION_FOLDER
from .allocation import Allocator
from .approval_checks import (
    EvidenceCommitted,
    EvidenceFilled,
    ExitsEnforceable,
    ExpectedNetSet,
    LiveFeaturesValidated,
)
from .candidates import CandidateBuilder
from .code_tree import GitCodeTree
from .decision_inputs import PlaybookSnapshot
from .decision_run import DecisionRun
from .decision_store import DecisionStore
from .evaluate import RuleEvaluator
from .history import PlaybookGit
from .lifecycle import StatusChanger
from .live_reports import CommittedLiveReports, LiveReports, RecomputedLiveReports
from .live_values import ComputedLiveFeatures
from .loader import PlaybookLoader, registry_path
from .opportunities import OpportunityFinder
from .registry import Registry, rewritten_history
from .rule_checks import CatastrophicCapWithinRisk
from .shadow import RealBooks


def _recompute_live_report(live_feature: str) -> Mapping:
    from ..composition import run_live_validation
    from ..config import load_app_config
    from ..models import now_ist

    return run_live_validation(load_app_config(), live_feature, now_ist().date()).summary()


def build_playbook_loader(root: Path = ROOT, reports: LiveReports | None = None) -> PlaybookLoader:
    folder = root / PLAYBOOK_FOLDER
    reports = reports or RecomputedLiveReports(CommittedLiveReports(LIVE_VALIDATION_FOLDER), _recompute_live_report)
    checks = (EvidenceFilled(), ExpectedNetSet(), EvidenceCommitted(PlaybookGit(root)), LiveFeaturesValidated(reports),
              ExitsEnforceable())  # fmt: skip
    return PlaybookLoader(
        folder, Registry(registry_path(folder)), checks, (CatastrophicCapWithinRisk(_risk_cap(root)),)
    )


def _risk_cap(root: Path) -> float:
    """The books' per-trade maximum loss from config.yaml `risk` (the one place the owner's limit is set)."""
    from ..config import load_app_config
    from ..constants import RISK_PROFILE_BOOKS
    from ..risk.profile_settings import profile_settings

    return profile_settings(load_app_config(), RISK_PROFILE_BOOKS).max_loss_per_trade_rs


def build_status_changer(root: Path = ROOT, reports: LiveReports | None = None) -> StatusChanger:
    return StatusChanger(build_playbook_loader(root, reports), PlaybookGit(root))


def registry_history_problems(root: Path = ROOT) -> list[str]:
    """Past registry rows edited in git history or in the working file (empty when append-only)."""
    path = registry_path(root / PLAYBOOK_FOLDER)
    versions = PlaybookGit(root).file_versions(path.relative_to(root).as_posix())
    current = [path.read_text(encoding="utf-8")] if path.is_file() else []
    return rewritten_history(versions + current)


def build_rule_evaluator(cfg: dict, root: Path = ROOT) -> RuleEvaluator:
    """Story D2: the opportunity finder on NSE's session calendar, the structures and cost model of the research (B2),
    and the risk manager with every owner limit (C2), all from config.yaml."""
    from ..books.paths import book_folder
    from ..composition import build_session_calendar, build_tradable_structures
    from ..constants import BOOKS, NIFTY_SYMBOL, RISK_PROFILE_BOOKS
    from ..research_engine.cycles import TradingDays
    from ..risk.profile_settings import profile_settings
    from ..risk.trade_costs import SimulatorTradeCosts
    from ..risk.wiring import build_risk_manager

    costs, cap = SimulatorTradeCosts(cfg["charges"]), profile_settings(cfg, RISK_PROFILE_BOOKS).max_loss_per_trade_rs
    structures = {structure.code: structure for structure in build_tradable_structures()}
    builder = CandidateBuilder(structures, costs, cap, cfg["lot_sizes"][NIFTY_SYMBOL])
    finder = OpportunityFinder(TradingDays(build_session_calendar()))
    real = RealBooks(BOOKS, [book_folder(root, book) for book in BOOKS])
    return RuleEvaluator(finder, builder, Allocator(build_risk_manager(cfg, root), costs), real)


def build_live_feature_values(cfg: dict, data) -> ComputedLiveFeatures:
    """B7's live 15:00 features over the research data the caller loaded for the day."""
    from ..composition import build_live_features

    return ComputedLiveFeatures(build_live_features(cfg), data)


def build_decision_run(cfg: dict, book: str, root: Path = ROOT) -> DecisionRun:
    """Story D3: D2's evaluator for the app (every C2 limit) writing into `journal/<book>/decisions/`; every chosen
    trade passes C4's hard validity first (its failures logged in `journal/<book>/validity_failures.csv`)."""
    from ..checks.wiring import build_trade_validator

    validator = build_trade_validator(cfg, book, root)
    return DecisionRun(build_rule_evaluator(cfg, root), DecisionStore(root, book), validator)


def snapshot_playbook(root: Path = ROOT) -> PlaybookSnapshot:
    """The playbook as it stands now: every version file, the registry and the commit they were read at."""
    folder = root / PLAYBOOK_FOLDER
    files = {path.name: path.read_text(encoding="utf-8") for path in sorted(folder.glob("*.yaml"))}
    registry = registry_path(folder)
    text = registry.read_text(encoding="utf-8") if registry.is_file() else ""
    return PlaybookSnapshot(files, text, PlaybookGit(root).head())


def build_code_tree(root: Path = ROOT) -> GitCodeTree:
    """Story D3, judge 80: the running fno/ and config.yaml, compared with a record's code commit before any replay."""
    return GitCodeTree(PlaybookGit(root))
