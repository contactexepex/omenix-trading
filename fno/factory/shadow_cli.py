"""The R1c commands of `python -m fno factory`: `question`, `freeze`, `verdict`, `shadows`. Research records only:
nothing here opens an account, fills a trade or places an order."""

from __future__ import annotations

from ..models import today_local

_HELP = {
    "freeze": "G4: freeze a planned idea as a registered shadow (commit the files)",
    "verdict": "G6: judge a shadow once, at its frozen sample, by its family's Holm",
}


def add_shadow_parsers(actions) -> None:
    question = actions.add_parser("question", help="register a research question (its Holm family; commit it)")
    question.add_argument("question_id")
    question.add_argument("text")
    question.add_argument("--alpha", type=float, required=True, help="the family's one-sided level, e.g. 0.01")
    for name, text in _HELP.items():
        actions.add_parser(name, help=text).add_argument("idea_id")
    actions.add_parser("shadows", help="the registered shadows the stop rule's Test B counts")


def question(args) -> list[str]:
    from .wiring import build_questions

    row = build_questions().add(args.question_id, args.text, args.alpha)
    return [f"question {row.question_id} registered (alpha {row.alpha:g}); commit research/factory/questions.csv"]


def freeze(args) -> list[str]:
    from .wiring import build_freeze, read_idea

    row = build_freeze().freeze(read_idea(args.idea_id), today_local())
    return [f"{args.idea_id}: G4 registered ({row.numbers}); commit research/ledger.csv and research/factory/gates.csv"]


def verdict(args) -> list[str]:
    from .wiring import build_verdicts, read_idea

    result = build_verdicts().judge(read_idea(args.idea_id), today_local())
    members = [f"  {m.version}: p {m.p:.4f} ({m.positions} of {m.sample} positions opened after {m.opened_after})"
               for m in result.members]  # fmt: skip
    word = "passed" if result.passed else "failed"
    if result.exploratory:
        word += " (exploratory data: it can never pass, FACTORY_RULES section 4)"
    return [f"{args.idea_id}: G6 {word} (Holm across {len(result.members)} shadows on {result.question_id}, alpha "
            f"{result.alpha:g}); never relabelled", *members,
            "miss share: not reported until E6b's missed-execution counter is merged (R1 Known limits)",
            "commit research/factory/gates.csv"]  # fmt: skip


def shadows(args) -> list[str]:
    from .wiring import build_registered_shadows

    found = build_registered_shadows().all()
    lines = [f"{s.version}: trial {s.trial_id}, sample {s.sample}, pass level {s.pass_level:g}, minimum useful net "
             f"{s.minimum_useful_net:g}, question {s.question_id}" for s in found]  # fmt: skip
    return lines or ["no registered shadow yet (Test B's R1 input is missing)"]


COMMANDS = {"question": question, "freeze": freeze, "verdict": verdict, "shadows": shadows}
