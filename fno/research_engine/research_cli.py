"""`python -m fno research run <experiment> --period discovery|challenge` (story B3): runs a registered experiment's
period and writes research/<experiment>/results_<period>.json and .md. The decisive period (the challenge) runs only
with its frozen protocol and then records the first run in the ledger (commit it with the results)."""

from __future__ import annotations

from pathlib import Path

from ..constants import (
    FEATURE_ATM_IV_MINUS_RV20_LIVE,
    FEATURE_EVENT_IN_WINDOW_LIVE,
    FEATURE_VIX_ABOVE_MEDIAN_LIVE,
    PERIOD_CHALLENGE,
    PERIOD_DISCOVERY,
)
from .experiment_1 import EXPERIMENT_1
from .ledger import Ledger
from .results_file import write_results

EXPERIMENTS = {EXPERIMENT_1.folder: EXPERIMENT_1}
LIVE_FEATURES = (FEATURE_ATM_IV_MINUS_RV20_LIVE, FEATURE_VIX_ABOVE_MEDIAN_LIVE, FEATURE_EVENT_IN_WINDOW_LIVE)


def add_research_parser(subparsers) -> None:
    research = subparsers.add_parser("research", help="run a registered experiment's period (story B3)")
    actions = research.add_subparsers(dest="research_cmd", required=True)
    run = actions.add_parser("run", help="run every policy and control of one period and write its results")
    run.add_argument("experiment", choices=sorted(EXPERIMENTS))
    run.add_argument("--period", required=True, choices=[PERIOD_DISCOVERY, PERIOD_CHALLENGE])
    live = actions.add_parser("validate-live", help="compare a live 15:00 feature with its close version (story B7)")
    live.add_argument("feature", choices=LIVE_FEATURES)
    research.set_defaults(func=cmd_research)


def cmd_research(args) -> int:
    return _validate_live(args) if args.research_cmd == "validate-live" else _run(args)


def _validate_live(args) -> int:
    """Writes research/live_validation/<feature>.json and prints the report's numbers and the use-rule verdict."""
    from ..composition import run_live_validation
    from ..config import ROOT, load_app_config
    from ..models import now_ist
    from ..storage.wiring import LIVE_VALIDATION_FOLDER
    from .results_file import results_json

    summary = run_live_validation(load_app_config(args.config), args.feature, now_ist().date()).summary()
    LIVE_VALIDATION_FOLDER.mkdir(parents=True, exist_ok=True)
    path = LIVE_VALIDATION_FOLDER / f"{args.feature}.json"
    path.write_text(results_json(summary), encoding="utf-8")
    numbers = {k: summary[k] for k in ("days", "agreement", "live_available", "largest_abs_difference", "validated")}
    print(
        f"{args.feature}: {numbers}; disagreement days {summary['disagreement_days']}; wrote {path.relative_to(ROOT)}"
    )
    return 0


def _run(args) -> int:
    from ..composition import build_experiment_runner, build_ledger
    from ..config import ROOT, load_app_config
    from .ledger import NotRegistered
    from .trial_guard import ProtocolNotFrozen

    experiment = EXPERIMENTS[args.experiment]
    try:
        document = build_experiment_runner(load_app_config(args.config)).run(experiment, args.period)
    except (NotRegistered, ProtocolNotFrozen) as refusal:
        print(f"refused: {refusal}")
        return 2
    decisive = experiment.period(args.period).decisive
    paths = record_run(build_ledger(), ROOT / "research" / experiment.folder, document, experiment.trial_ids, decisive)
    print("wrote " + " and ".join(str(p.relative_to(ROOT)) for p in paths))
    if decisive:
        print("first run recorded in research/ledger.csv: commit it with the results")
    return 0


def record_run(ledger: Ledger, folder: Path, document: dict, trial_ids, decisive: bool) -> tuple[Path, Path]:
    """Writes the results and, for the decisive period, each trial's first run. The run's commit is read before any
    write, so a failed git read leaves nothing written; a rerun writes both."""
    run_commit = ledger.git.head() if decisive else ""
    paths = write_results(folder, document)
    for trial_id in trial_ids if decisive else ():
        ledger.mark_run(trial_id, run_commit)
    return paths
