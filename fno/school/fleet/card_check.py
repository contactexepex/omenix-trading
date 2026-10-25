"""A comparison card edited without its D6 rows is loud (orchestrator's ruling, 23 Oct 2026; the MS-P1j runbook):
after the decisions' seal, each sealed decision is put to h's counting rule at the seal's receipt commit, and when
any is `comparison_card_mismatch` the run says so in one line, by that name and nothing else (never "not yet
counted"), and the CLI exits 1 so the daily run alerts #fno-desk. No record changes."""

import re
from collections.abc import Callable

from ..contracts.records import DecisionRecord
from ..contracts.seal import Seal
from ..registration.counting import CountCandidate, CountingRule, NotCounted

MISMATCH_LINE = ("comparison_card_mismatch: {n} of {m} decisions do not count until D6 rows name card v{version}; "
                 "see the MS-P1j runbook")  # fmt: skip
VERSION = re.compile(r"^version:\s*(\d+)\s*$", re.MULTILINE)  # the card's factory block names its version


def card_version(text: str) -> str:
    found = VERSION.search(text)
    return found.group(1) if found else "?"


class CardMismatchCheck:
    def __init__(self, rule: CountingRule, card_text: Callable[[str], str]):
        """`card_text(commit)`: the comparison card as committed there."""
        self.rule, self.card_text = rule, card_text

    def __call__(self, records: tuple[DecisionRecord, ...], seal: Seal) -> tuple[str, ...]:
        verdicts = [self.rule.verdict(CountCandidate(r.session, r.road, r.decision.driver_id, r.card_sha256,
                                                     seal.commit)) for r in records]  # fmt: skip
        mismatched = [v for v in verdicts if v.reason == NotCounted.COMPARISON_CARD_MISMATCH]
        if not mismatched:
            return ()
        version = card_version(self.card_text(mismatched[0].card_commit))
        return (MISMATCH_LINE.format(n=len(mismatched), m=len(records), version=version),)


def no_check(records: tuple[DecisionRecord, ...], seal: Seal) -> tuple[str, ...]:
    """A replay's seals name no commit the rule could judge."""
    return ()
