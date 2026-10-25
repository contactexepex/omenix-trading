"""`python -m fno playbook check` and `python -m fno playbook set-status` (story D1). Research and paper only: a
playbook decides what the paper books may trade; nothing here places an order."""

from __future__ import annotations

from datetime import date

from ..constants import APPROVER_DESK, APPROVER_HARD_LOSS_RULE, APPROVER_OWNER, PlaybookStatus

EXIT_REFUSED = 2


def add_playbook_parser(subparsers) -> None:
    playbook = subparsers.add_parser("playbook", help="check the playbook, or change a strategy version's status")
    actions = playbook.add_subparsers(dest="playbook_cmd", required=True)
    actions.add_parser("check", help="load every playbook file against the registry; list the approved versions")
    change = actions.add_parser("set-status", help="append a status change to playbook/registry.csv (commit it)")
    change.add_argument("name")
    change.add_argument("version", type=int)
    change.add_argument("status", choices=list(PlaybookStatus))
    change.add_argument("--by", required=True, choices=[APPROVER_OWNER, APPROVER_DESK, APPROVER_HARD_LOSS_RULE])
    change.add_argument("--on", type=date.fromisoformat, required=True, help="date of the change (YYYY-MM-DD)")
    change.add_argument("--evidence-commit", default="", help="commit holding the evidence (default: HEAD)")
    playbook.set_defaults(func=cmd_playbook)


def cmd_playbook(args) -> int:
    from .fields import PlaybookError
    from .wiring import build_playbook_loader, build_status_changer, registry_history_problems

    try:
        if args.playbook_cmd == "check":
            problems = registry_history_problems()
            if problems:
                raise PlaybookError("registry.csv history", "; ".join(problems))
            return _print_playbook(build_playbook_loader().load())
        row = build_status_changer().change(
            args.name, args.version, PlaybookStatus(args.status), args.by, args.on, args.evidence_commit
        )
    except PlaybookError as refused:
        print(f"refused: {refused}")
        return EXIT_REFUSED
    print(f"recorded: {row.name} v{row.version} -> {row.status} by {row.approved_by} on {row.changed_on}")
    return 0


def _print_playbook(playbook) -> int:
    for strategy in playbook.strategies:
        print(f"{strategy.file_name}: {strategy.status} (rule sha256 {strategy.parameters_sha256[:12]})")
    for drift in playbook.drifted:
        print(
            f"{drift.strategy.file_name}: NOT approved, live feature drift (desk scorecard pauses it): {drift.reason}"
        )
    approved = [s.file_name for s in playbook.approved()]
    print(f"approved for paper: {', '.join(approved) if approved else 'none (Book 1 trades nothing)'}")
    return 0
