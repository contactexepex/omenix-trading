"""The factory's fixed names (story R1), used only by `fno/factory/`: module-specific constants (CLAUDE.md), kept out
of `fno/constants.py`, which is at the 350-line limit."""

from enum import StrEnum

IDEAS_FOLDER = "research/ideas"
TEMPLATE_CARD = "TEMPLATE.md"
GATES_FILE = "research/factory/gates.csv"
QUESTIONS_FILE = "research/factory/questions.csv"
QUESTION_COLUMNS = ("question_id", "question", "alpha")
GATE_COLUMNS = ("trial_id", "gate", "outcome", "on", "commit", "numbers")
CARD_FENCE = "factory"  # the card's machine block: a fenced ```factory YAML block
IDEA_KIND = "prospective"  # every factory idea is registered before any of its results exists
BACKFILLED = "backfilled=yes"  # a G0 row written by R1a for a card registered by hand before the code
NUMBERS_PATTERN = r"^([a-z_0-9]+=[^;,=\s]+(;[a-z_0-9]+=[^;,=\s]+)*)?$"  # k=v;k=v, or empty
DEFAULT_ALPHA = 0.01  # FACTORY_RULES section 5's example level (1% one-sided)
DATA_SPEND_FILE = "research/DATA_SPEND.md"
BOUND_LEVEL = 0.90  # FACTORY_RULES section 2: the lower one-sided 90% bound of a measured mean
THIN_MARGIN_RATIO = 2.0  # FACTORY_RULES section 2: expected gross under 2 x cost is a warning, never a pass mark
PLAN_YEARS_LIMIT = 3.0  # FACTORY_RULES section 3: a sample plan above 3 years is an exploratory_shadow only


class Gate(StrEnum):
    IDEA_CARD = "G0"
    SCREEN = "G1"
    DATA_SPEND = "G2"
    SAMPLE_PLAN = "G3"
    REGISTRATION = "G4"
    VERDICT = "G6"


class Outcome(StrEnum):
    IDEA = "idea"
    PASSED = "passed"
    SCREENED_OUT = "screened_out"
    FRESH = "fresh"
    EXPLORATORY = "exploratory"
    PLANNED = "planned"
    EXPLORATORY_SHADOW = "exploratory_shadow"
    REGISTERED = "registered"
    FAILED = "failed"


GATE_OUTCOMES = {
    Gate.IDEA_CARD: (Outcome.IDEA,),
    Gate.SCREEN: (Outcome.PASSED, Outcome.SCREENED_OUT),
    Gate.DATA_SPEND: (Outcome.FRESH, Outcome.EXPLORATORY),
    Gate.SAMPLE_PLAN: (Outcome.PLANNED, Outcome.EXPLORATORY_SHADOW),
    Gate.REGISTRATION: (Outcome.REGISTERED,),
    Gate.VERDICT: (Outcome.PASSED, Outcome.FAILED),
}


class GrossKind(StrEnum):
    """Where an idea's gross edge comes from (FACTORY_RULES section 2, input 1)."""

    MEASURED = "measured"  # a measured distribution: mean, SD and n
    PUBLISHED = "published"  # its least favourable published value
    ARITHMETIC = "arithmetic"  # stated in full; its least favourable input
    NONE = "none"  # no source: "no stated edge"
    ASSUMED_HURDLE = "assumed_hurdle"  # a cost-hurdle study (judge 97): never a G1 pass
