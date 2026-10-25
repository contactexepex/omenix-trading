"""`python -m fno evaluation check|freeze|order` (story S1).
- `check` runs the completeness check of the protocol and of the real-money gate (RM1); `--decided` also requires
  every item of both decided by the owner.
- `freeze` writes the freeze record and registers the protocol in the ledger; commit both at once.
- `order` checks that the freeze precedes each book's first counted decision.
- `verify` checks that the latest freeze's files and settings are unchanged (a suite test runs it).
`check`, `freeze` and `verify` take `--protocol breadth` for BR1's protocol (story BR1a); the default is S1's.
None of them computes a result or places an order."""

from __future__ import annotations

from datetime import date

from ..constants import BOOKS, PROTOCOL_BREADTH, PROTOCOL_EVALUATION
from ..models import today_local

EXIT_FAILED = 2


def add_evaluation_parser(subparsers) -> None:
    evaluation = subparsers.add_parser("evaluation", help="the evaluation protocol of the three books (story S1)")
    actions = evaluation.add_subparsers(dest="evaluation_cmd", required=True)
    check = actions.add_parser("check", help="completeness check of the protocol and the real-money gate")
    check.add_argument("--decided", action="store_true", help="also require every item decided by the owner")
    freeze = actions.add_parser("freeze", help="freeze the decided protocol (commit the record and the ledger at once)")
    verify = actions.add_parser("verify", help="the latest freeze's files and settings are unchanged")
    for action in (check, freeze, verify):
        action.add_argument("--protocol", choices=(PROTOCOL_EVALUATION, PROTOCOL_BREADTH), default=PROTOCOL_EVALUATION)
    order = actions.add_parser("order", help="the freeze precedes each book's first counted decision")
    order.add_argument("--version", type=int, default=1)
    order.add_argument("--common-start", type=date.fromisoformat, help="without it every decision counts")
    evaluation.set_defaults(func=cmd_evaluation)


def _check(decided: bool, name: str = PROTOCOL_EVALUATION) -> int:
    from ..config import ROOT
    from .completeness import completeness_problems, undecided_items
    from .protocol import parse_protocol
    from .wiring import protocol_definition

    definition = protocol_definition(name)
    text = (ROOT / definition.protocol_file).read_text(encoding="utf-8")
    protocol = parse_protocol(text)
    problems = completeness_problems(text, protocol, definition.required_items)
    undecided = undecided_items(protocol) if decided else []
    for problem in problems:
        print(f"incomplete: {problem}")
    if undecided:
        print(f"not decided by the owner ({len(undecided)}): {', '.join(undecided)}")
    if not (problems or undecided):
        print(f"{definition.protocol_file} version {protocol.version}: complete" + (" and decided" if decided else ""))
    gate_failed = _check_gate(ROOT, decided) if definition.requires_gate else False
    return EXIT_FAILED if problems or undecided or gate_failed else 0


def _check_gate(root, decided: bool) -> bool:
    """Prints the real-money gate's problems, or that it is ready; True when it failed (story RM1)."""
    from .gate import GATE_FILE, gate_problems

    file = root / GATE_FILE
    problems = gate_problems(file.read_text(encoding="utf-8"), decided) if file.is_file() else ["missing"]
    for problem in problems:
        print(f"gate: {problem}")
    if not problems:
        print(f"{GATE_FILE}: complete" + (" and decided" if decided else ""))
    return bool(problems)


def _freeze(name: str = PROTOCOL_EVALUATION) -> int:
    from .freeze import FreezeRefused
    from .wiring import build_freezer, protocol_definition

    try:
        record = build_freezer(protocol=name).freeze(today_local())
    except FreezeRefused as refused:
        print(f"not frozen: {refused}")
        return EXIT_FAILED
    path = protocol_definition(name).freeze_path(record.version)
    print(f"wrote {path} ({len(record.hashes)} targets) and its ledger row: commit both now")
    return 0


def _order(version: int, common_start: date | None) -> int:
    from ..config import ROOT
    from .order import first_counted_decision, order_problems
    from .wiring import build_protocol_git

    git = build_protocol_git()
    firsts = [first_counted_decision(ROOT, git, book, common_start) for book in BOOKS]
    problems = order_problems(git, version, [f for f in firsts if f is not None])
    for problem in problems:
        print(f"out of order: {problem}")
    if not problems:
        print(f"v{version}: the freeze precedes every counted decision ({sum(f is not None for f in firsts)} books)")
    return EXIT_FAILED if problems else 0


def _verify(name: str = PROTOCOL_EVALUATION) -> int:
    from ..config import ROOT
    from .order import verify
    from .wiring import protocol_definition

    problems = verify(ROOT, protocol_definition(name))
    for problem in problems:
        print(f"changed: {problem}")
    if not problems:
        print("the latest freeze's files and settings are unchanged (or nothing is frozen yet)")
    return EXIT_FAILED if problems else 0


def cmd_evaluation(args) -> int:
    if args.evaluation_cmd == "check":
        return _check(args.decided, args.protocol)
    if args.evaluation_cmd == "verify":
        return _verify(args.protocol)
    if args.evaluation_cmd == "freeze":
        return _freeze(args.protocol)
    return _order(args.version, args.common_start)
