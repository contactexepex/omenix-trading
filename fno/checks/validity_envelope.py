"""C4's Book 2 mode (story D4, criteria 2, 4, 5 and 9): the playbook mode's checks on the version the trade claims,
with lots allowed down to 1 but never above the version's, then the authority envelope of that version, checked
independently of the decider, among the versions D2 found eligible that day (fired with a valid candidate), never
the approved list alone. The envelope file's hash must equal the version's registered D6 component
(`trade_envelope:<name>-v<n>`): a file edited after registration fails closed. The action must be `allowed`: a
`shadow-only` action is never the account's trade (the account takes the rule default), and a forbidden one fails.
A damaged envelope file fails the named `envelope` check."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import date

from ..playbook.envelope import AuthorityEnvelope, BookTerms, TradeEnvelope, VersionKey
from ..playbook.envelope_files import EnvelopeError, component_key
from .validity_evidence import Evidence
from .validity_modes import PlaybookMode, ValidityMode
from .validity_proposal import CheckResult, ValidityProposal
from .validity_shapes import Shape

RegisteredComponents = Callable[[str, date], Mapping[str, str]]  # (book, day) -> the active D6 version's components


def at_most_lots(lots: int, version_lots: int) -> bool:
    return 1 <= lots <= version_lots


class EnvelopeMode(ValidityMode):
    name = "envelope"

    def __init__(self, shapes: Mapping[str, Shape], envelopes: Callable[[], Mapping[VersionKey, TradeEnvelope]],
                 registered: RegisteredComponents):  # fmt: skip
        self.playbook = PlaybookMode(shapes, lots_rule=at_most_lots)
        self.envelopes, self.registered = envelopes, registered

    def checks(self, proposal: ValidityProposal, evidence: Evidence | None) -> list[CheckResult]:
        results = self.playbook.checks(proposal, evidence)
        strategy = proposal.strategy
        if strategy is None:
            return results
        try:
            envelopes = self.envelopes()
        except EnvelopeError as damaged:
            return results + [CheckResult("envelope", False, f"damaged trade envelope: {damaged}")]
        key = strategy.key
        envelope = envelopes.get(key)
        if envelope is None:
            return results + [CheckResult("envelope", False, f"no trade envelope for {key[0]} v{key[1]}")]
        component = self.registered(proposal.book, proposal.day).get(component_key(key))
        shown = f"file {envelope.sha256[:12]} vs registered {(component or 'none')[:12]}"
        results.append(CheckResult("envelope_registered", envelope.sha256 == component, shown))
        if proposal.rule_default is None:
            return results + [CheckResult("envelope", False, "no rule default given: the rules offered no trade")]
        choice = BookTerms(key, proposal.width, proposal.lots)
        verdict = AuthorityEnvelope(envelopes).permits(choice, proposal.rule_default, strategy, proposal.eligible)
        verdict_check = CheckResult("envelope", verdict.allowed, f"{verdict.status}: {verdict.reason}")
        return results + [verdict_check]
