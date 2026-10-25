"""`python -m fno factory register | backfill | screen | spend | plan | status | report` (stories R1a and R1b), plus
R1c's `question | freeze | verdict | shadows` (`shadow_cli.py`). Research records only: nothing here runs a test, opens
an account or places an order."""

from __future__ import annotations

from ..models import today_local
from .constants import DEFAULT_ALPHA
from .shadow_cli import COMMANDS as SHADOW_COMMANDS
from .shadow_cli import add_shadow_parsers

EXIT_REFUSED = 2
_GATE_HELP = {
    "screen": "G1: the cost wall on the card's committed inputs (logged once)",
    "spend": "G2: the data spend of the rows the card names in research/DATA_SPEND.md (logged once)",
    "plan": "G3: the sample plan from the card's SD, frequency and pass level and its G1 net (logged once)",
}


def add_factory_parser(subparsers) -> None:
    factory = subparsers.add_parser("factory", help="the strategy factory: register idea cards, show the trial count")
    actions = factory.add_subparsers(dest="factory_cmd", required=True)
    register = actions.add_parser("register", help="G0: write the card's ledger row and its gate-log row (commit them)")
    register.add_argument("idea_id")  # always dated today: a past date would weaken the ledger's record (judge 261)
    backfill = actions.add_parser("backfill", help="the `idea` row of a card registered by hand before R1's code")
    backfill.add_argument("idea_id")
    for gate, text in _GATE_HELP.items():
        actions.add_parser(gate, help=text).add_argument("idea_id")
    status = actions.add_parser("status", help="one idea's trial k of K and its last gate")
    status.add_argument("idea_id")
    report = actions.add_parser("report", help="every idea's trial k of K and last gate, and expected false passes")
    report.add_argument("--alpha", type=float, default=DEFAULT_ALPHA, help="one-sided pass level (default 0.01)")
    add_shadow_parsers(actions)
    factory.set_defaults(func=cmd_factory)


def cmd_factory(args) -> int:
    from ..research_engine.ledger import NotRegistered
    from .card import CardError
    from .gate_log import GateLogError
    from .gate_order import GateStepError
    from .questions import QuestionError
    from .registration import RegistrationError

    try:
        lines = _COMMANDS[args.factory_cmd](args)
    except (CardError, GateLogError, GateStepError, QuestionError, RegistrationError, NotRegistered) as refused:
        print(f"refused: {refused}")
        return EXIT_REFUSED
    print("\n".join(lines))
    return 0


def _register(args) -> list[str]:
    from .wiring import build_registration, read_idea

    files = build_registration().register(read_idea(args.idea_id), today_local())
    return [f"registered: {args.idea_id} (G0 idea); commit together: {' '.join(files)}"]


def _backfill(args) -> list[str]:
    from .wiring import build_registration, read_idea

    files = build_registration().backfill(read_idea(args.idea_id))
    return [f"back-filled: {args.idea_id} (G0 idea); commit together: {' '.join(files)}"]


def _gate(args) -> list[str]:
    from . import gate_numbers
    from .wiring import build_gate_steps, read_idea

    run = getattr(build_gate_steps(), args.factory_cmd)
    lines = getattr(gate_numbers, f"{args.factory_cmd}_lines")
    return [*lines(args.idea_id, run(read_idea(args.idea_id), today_local())), "commit research/factory/gates.csv"]


def _status(args) -> list[str]:
    from .status import idea_line
    from .wiring import build_gate_log, build_trial_count, read_idea

    card, gates = read_idea(args.idea_id), build_gate_log()
    gates.require_append_only()
    return [idea_line(card, build_trial_count(), gates.last(card.trial_id))]


def _report(args) -> list[str]:
    from .status import false_pass_line, idea_line
    from .wiring import build_gate_log, build_trial_count, read_all_ideas

    cards, gates, count = read_all_ideas(), build_gate_log(), build_trial_count()
    gates.require_append_only()
    passes = count.false_passes(args.alpha, (card.trial_id for card in cards if card.measurement))
    return [false_pass_line(count, passes), *(idea_line(card, count, gates.last(card.trial_id)) for card in cards)]


_COMMANDS = {"register": _register, "backfill": _backfill, "screen": _gate, "spend": _gate, "plan": _gate,
             "status": _status, "report": _report, **SHADOW_COMMANDS}  # fmt: skip
