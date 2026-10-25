"""Plain words for each cause and modifier (story MS-INS, part e): the loser form and the winner form (325 section
6.1's table), as the review and the 20:05 line print them. No contract, strike or price ever appears in a label."""

from ..contracts import Cause, Modifier

CAUSE_WORDS = {
    Cause.MOVE_BEYOND_RANGE: ("move beyond the expected range", "move beyond the expected range"),
    Cause.WRONG_DIRECTION: ("wrong direction", "right direction"),
    Cause.VOLATILITY_ROSE: ("volatility rose", "volatility fell"),
    Cause.VOLATILITY_COLLAPSED: ("volatility collapsed", "volatility rose"),
    Cause.TIME_DECAY: ("time decay", "time decay earned"),
    Cause.GAP_THROUGH_STOP: ("gap through the stop", "gap through the stop"),
    Cause.SCHEDULED_EVENT_SHOCK: ("scheduled event shock", "scheduled event shock"),
    Cause.UNSCHEDULED_SHOCK: ("market-wide shock", "market-wide shock"),
    Cause.COSTS_ATE_EDGE: ("costs ate the edge", "costs ate the edge"),
    Cause.BAD_PRICE_OR_DATA: ("bad price or data", "bad price or data"),
    Cause.EXIT_WHIPSAW: ("exit whipsaw", "the exit cost the gain"),
    Cause.NORMAL_NOISE: ("normal noise", "normal noise"),
    Cause.RULE_BROKEN: ("rule broken", "rule broken"),
}
MODIFIER_WORDS = {Modifier.HARD_ROAD: "hard road", Modifier.BAD_DRIVER: "bad driver",
                  Modifier.NOT_TESTABLE: "road not compared yet", Modifier.NONE: ""}  # fmt: skip
UNCLASSIFIED = "unclassified"


def cause_words(cause: Cause, winner: bool) -> str:
    return CAUSE_WORDS[cause][1 if winner else 0]
