"""Book 2's authority envelope (story D4; design 12.2): which actions Book 2's AI may take on a playbook version. Each
action of a closed list has a status `allowed`, `shadow-only` or `forbidden`; an action the envelope does not list is
forbidden. The actions a choice uses are derived from its terms against the rule default (D2), never claimed by the
decider, so a choice cannot say one thing and do another. The envelope of the version actually traded governs every
action of the trade (judge 207). A choice that trades when the rules offered no trade is always refused: the envelope
never creates a trade the rules did not offer. The rule default and the eligible versions come from D2's evaluation,
never from the decider (judge 260)."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from enum import StrEnum


class EnvelopeAction(StrEnum):
    FOLLOW_RULE = "follow_rule"
    CHOOSE_STRATEGY = "choose_strategy"
    NO_TRADE = "no_trade"
    CHOOSE_WIDTH = "choose_width"
    REDUCE_LOTS = "reduce_lots"


class ActionStatus(StrEnum):
    ALLOWED = "allowed"
    SHADOW_ONLY = "shadow-only"
    FORBIDDEN = "forbidden"


SEVERITY = (ActionStatus.ALLOWED, ActionStatus.SHADOW_ONLY, ActionStatus.FORBIDDEN)  # the strictest status wins
VersionKey = tuple[str, int]  # (playbook name, version)


@dataclass(frozen=True)
class BookTerms:
    """A trade on one version: its width and lots (the structure and strikes are the version's, set by code)."""

    version: VersionKey
    width: float
    lots: int


@dataclass(frozen=True)
class TradeEnvelope:
    version: VersionKey
    statuses: Mapping[EnvelopeAction, ActionStatus]
    sha256: str  # of the file's bytes: the D6 component `trade_envelope:<name>-v<n>`

    def status(self, action: EnvelopeAction) -> ActionStatus:
        return self.statuses.get(action, ActionStatus.FORBIDDEN)


@dataclass(frozen=True)
class Verdict:
    status: ActionStatus
    actions: tuple[EnvelopeAction, ...]
    reason: str

    @property
    def allowed(self) -> bool:
        return self.status == ActionStatus.ALLOWED


class AuthorityEnvelope:
    def __init__(self, envelopes: Mapping[VersionKey, TradeEnvelope]):
        self.envelopes = dict(envelopes)

    def permits(self, choice: BookTerms | None, rule_default: BookTerms | None, version,
                eligible: Collection[VersionKey]) -> Verdict:  # fmt: skip
        """`choice` and `rule_default` are None for no trade; `version` is the traded version's playbook entry."""
        if choice is None and rule_default is None:  # nothing was offered and nothing is traded: no envelope needed
            return Verdict(ActionStatus.ALLOWED, (EnvelopeAction.FOLLOW_RULE,), "the rules offered no trade")
        if choice is None:
            return self._verdict(
                self.envelopes.get(rule_default.version), (EnvelopeAction.NO_TRADE,), rule_default.version
            )
        if rule_default is None:
            return _forbidden((), "the rules offered no trade: the envelope never creates one")
        if choice.version not in eligible:
            return _forbidden((), f"{_name(choice.version)} is not eligible on the day")
        problem = _terms_problem(choice, version)
        if problem:
            return _forbidden((), problem)
        return self._verdict(
            self.envelopes.get(choice.version), _actions(choice, rule_default, version), choice.version
        )

    def _verdict(self, envelope: TradeEnvelope | None, actions: tuple[EnvelopeAction, ...], key) -> Verdict:
        if envelope is None:
            return _forbidden(actions, f"no trade envelope for {_name(key)}" if key else "no trade envelope")
        statuses = [envelope.status(a) for a in actions]
        worst = max(statuses, key=SEVERITY.index)
        detail = ", ".join(f"{a} {s}" for a, s in zip(actions, statuses))
        return Verdict(worst, actions, f"{_name(key)}: {detail}")


def _actions(choice: BookTerms, rule_default: BookTerms, version) -> tuple[EnvelopeAction, ...]:
    """The actions the choice uses. On the rule default's own version its width and lots are the reference; on another
    version the reference is that version's own terms (its widest width and its lots)."""
    same = choice.version == rule_default.version
    width, lots = (
        (rule_default.width, rule_default.lots) if same else (version.structure.widths[0], version.structure.lots)
    )
    actions = [] if same else [EnvelopeAction.CHOOSE_STRATEGY]
    if choice.width != width:
        actions.append(EnvelopeAction.CHOOSE_WIDTH)
    if choice.lots < lots:
        actions.append(EnvelopeAction.REDUCE_LOTS)
    return tuple(actions) or (EnvelopeAction.FOLLOW_RULE,)


def _terms_problem(choice: BookTerms, version) -> str:
    spec = version.structure
    if choice.width not in spec.widths:
        return f"width {choice.width:g} is not in the version's set {list(spec.widths)}"
    if choice.lots > spec.lots:
        return f"{choice.lots} lots is more than the version's {spec.lots}: size may only be reduced"
    if choice.lots < 1:
        return "at least 1 lot"
    return ""


def _forbidden(actions: tuple[EnvelopeAction, ...], reason: str) -> Verdict:
    return Verdict(ActionStatus.FORBIDDEN, actions, reason)


def _name(key: VersionKey | None) -> str:
    return f"{key[0]} v{key[1]}" if key else "no version"


@dataclass(frozen=True)
class Resolution:
    """What the account does with a verdict, and what is only recorded (criterion 3; F5 criterion 2)."""

    account: BookTerms | None  # the trade the account takes; None is no trade
    shadow: BookTerms | None  # a shadow-only action, recorded for scoreboard A and not scored until S3 reads it
    attempted: BookTerms | None  # a forbidden choice, recorded, never traded


def resolve(choice: BookTerms | None, rule_default: BookTerms | None, verdict: Verdict) -> Resolution:
    if verdict.status == ActionStatus.ALLOWED:
        return Resolution(choice, None, None)
    if verdict.status == ActionStatus.SHADOW_ONLY:
        return Resolution(rule_default, choice, None)
    return Resolution(None, None, choice)
