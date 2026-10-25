"""`SafetyLaws` (story 3.3): runs every law on a proposal, in a fixed order, and keeps every result, so a refusal
names all its reasons. Only these laws stop a paper trade; none resizes or changes a proposal (they receive frozen
objects and return results only)."""

from collections.abc import Sequence
from datetime import date

from ..constants import RefusalReason
from ..contracts.decisions import Proposal
from ..contracts.safety import AccountView, LawResult, SafetyLaw
from ..contracts.snapshot import SlotSnapshot


class SafetyLaws:
    def __init__(self, laws: Sequence[SafetyLaw]):
        names = [law.name for law in laws]
        if not laws or len(set(names)) != len(names):
            raise ValueError(f"the laws need distinct names: {names}")
        self.laws = tuple(laws)

    def check(self, proposal: Proposal, account: AccountView, snapshot: SlotSnapshot,
              session: date) -> tuple[LawResult, ...]:  # fmt: skip
        if snapshot.session != session:
            raise ValueError(f"the laws check a proposal at its own session's snapshot ({session})")
        return tuple(law.check(proposal, account, snapshot, session) for law in self.laws)


def refusals(results: Sequence[LawResult]) -> tuple[RefusalReason, ...]:
    """Every refusal reason, once each, in the laws' order; empty when every law passed."""
    return tuple(dict.fromkeys(r.reason for r in results if not r.passed))
