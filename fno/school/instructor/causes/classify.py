"""One primary cause and up to two secondary (story MS-INS, part c): the firing causes in the frozen order of
`research/school/INSTRUCTOR_V1.md`, causes 2-5 ranked by the size of their component; and the hard-road or bad-driver
modifier from the controls on the same road-slot (327 correction 2)."""

from datetime import date

from ....models import IST
from ..contracts import MAX_SECONDARY, Attribution, Cause, Classification, HeldPath, Modifier, record_sha256
from .evidence import Controls, Evidence, EvidenceBuilder
from .rules import verdicts

HEAD = (Cause.RULE_BROKEN, Cause.BAD_PRICE_OR_DATA, Cause.GAP_THROUGH_STOP, Cause.SCHEDULED_EVENT_SHOCK,
        Cause.UNSCHEDULED_SHOCK, Cause.MOVE_BEYOND_RANGE, Cause.EXIT_WHIPSAW)  # fmt: skip
GREEK_CAUSES = (Cause.WRONG_DIRECTION, Cause.VOLATILITY_ROSE, Cause.VOLATILITY_COLLAPSED, Cause.TIME_DECAY)
TAIL = (Cause.COSTS_ATE_EDGE, Cause.NORMAL_NOISE)


def ordered(ev: Evidence) -> tuple[Cause, ...]:
    """Every cause in the frozen precedence for this path: causes 2-5 by their component's absolute size."""
    a = ev.attribution
    size = {} if a is None else {Cause.WRONG_DIRECTION: a.delta, Cause.VOLATILITY_ROSE: a.vega,
                                 Cause.VOLATILITY_COLLAPSED: a.vega, Cause.TIME_DECAY: a.theta}  # fmt: skip
    greek = sorted(GREEK_CAUSES, key=lambda c: (-abs(size.get(c, 0.0)), GREEK_CAUSES.index(c)))
    return HEAD + tuple(greek) + TAIL


def modifier(net: float, controls: Controls | None) -> Modifier:
    if controls is None or controls.ref_net is None or controls.rc1_net is None:
        return Modifier.NOT_TESTABLE
    if controls.ref_net < 0 and controls.rc1_net < 0:
        return Modifier.HARD_ROAD
    if net < 0 and controls.ref_net >= 0 and controls.rc1_net >= 0:
        return Modifier.BAD_DRIVER
    return Modifier.NONE


def causes_of(ev: Evidence) -> tuple[Cause | None, tuple[Cause, ...], tuple[Cause, ...]]:
    """The primary cause (None: unclassified), up to two secondary, and the causes not testable."""
    found = verdicts(ev)
    firing = [c for c in ordered(ev) if found[c]]
    primary = firing[0] if firing else None
    return primary, tuple(firing[1 : 1 + MAX_SECONDARY]), tuple(c for c in Cause if found[c] is None)


class Classifier:
    def __init__(self, evidence: EvidenceBuilder, rules_sha256: str):
        self.evidence, self.rules_sha256 = evidence, rules_sha256

    def classify(self, path: HeldPath, attribution: Attribution | None, controls: Controls | None, as_of: date,
                 corrects: str = "") -> Classification:  # fmt: skip
        """`as_of`: the session whose run classifies, the cut-off of what the evidence may know."""
        primary, secondary, not_testable = causes_of(self.evidence.build(path, attribution, controls, as_of))
        outcome = path.outcome
        return Classification(
            position_id=outcome.position_id,
            driver_id=outcome.driver_id,
            road=outcome.road,
            closed_on=outcome.exit.filled_at.astimezone(IST).date(),
            is_ticket=outcome.is_ticket,
            net=outcome.net,
            primary=primary,
            secondary=secondary,
            not_testable=not_testable,
            modifier=modifier(outcome.net, controls),
            rules_sha256=self.rules_sha256,
            corrects=corrects,
            outcome_sha256=record_sha256(outcome),
        )
