"""The practice composition of the fill port (story 7.2, MS-SIM; orchestrator, 22 Oct 2026, design A): the simulator's
root, and only it, builds through here. A quote whose size was never measured fills with no size limit; every other
rule (validity, two sides, the touch, charges, settlement) is the live port's. No live module imports this one (tests
pin it)."""

from .quote_rules import QuoteRules
from .school_fills import SchoolFills
from .wiring import build_settlement_source

PRACTICE = QuoteRules(practice=True)


def build_practice_fill_port(cfg: dict) -> SchoolFills:
    return SchoolFills(cfg["charges"], build_settlement_source(), PRACTICE)
