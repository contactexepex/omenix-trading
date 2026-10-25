"""Experiment 1 as data (research/2026-10-12-experiment-1/PROTOCOL.md, sections 2, 6, 7 and 8; story B3). Every rule
is the protocol's formula; trial ids are the ledger's rows 22-31."""

from __future__ import annotations

from datetime import date

from .. import constants as c
from .experiments import BranchTest, Experiment, Period, PolicySpec, StatisticsTerms
from .policies import AllOf, Always, AnyOf, IsFalse, IsTrue, Known, NotPositive, Positive, Rule, RulePolicy

F1, F2, F3 = c.FEATURE_ATM_IV_MINUS_RV20, c.FEATURE_VIX_ABOVE_MEDIAN, c.FEATURE_EVENT_IN_WINDOW
SF, SC, BF = c.STRUCTURE_SHORT_IRON_FLY, c.STRUCTURE_SHORT_CONDOR, c.STRUCTURE_LONG_IRON_FLY
FOLDER = "2026-10-12-experiment-1"
SEED = 20261012


def _policy(code: str, *rules: tuple) -> RulePolicy:
    return RulePolicy(code, tuple(Rule(condition, action) for condition, action in rules))


P4 = _policy("P4", (Positive(F1), SC))
POLICIES = (
    PolicySpec(_policy("P1", (Always(), SC)), "22"),
    PolicySpec(_policy("P2", (Always(), SF)), "23"),
    PolicySpec(_policy("P3", (Always(), BF)), "24"),
    PolicySpec(P4, "25", _policy("P4 opposite", (NotPositive(F1), SC)), ("P1",)),
    PolicySpec(
        _policy("P5", (Positive(F1), SC), (NotPositive(F1), BF)),
        "26",
        _policy("P5 opposite", (Positive(F1), BF), (NotPositive(F1), SC)),
        ("P1", "P4"),
        (BranchTest("bf_branch", (("P5", BF),), BF, above_zero=True),),
    ),
    PolicySpec(
        _policy("P6", (AllOf((Positive(F1), IsFalse(F3))), SC)),
        "27",
        _policy("P6 opposite", (AnyOf((NotPositive(F1), AllOf((Known(F1), IsTrue(F3))))), SC)),
        ("P1", "P4"),
        (BranchTest("event_filter", (("P4", SC), ("P6", None)), SC, above_zero=False),),
    ),
    PolicySpec(_policy("P7", (IsTrue(F2), SC)), "28", _policy("P7 opposite", (IsFalse(F2), SC)), ("P1",)),
    PolicySpec(_policy("P8", (Positive(F1), SF)), "29", _policy("P8 opposite", (NotPositive(F1), SF)), ("P2",)),
)

EXPERIMENT_1 = Experiment(
    folder=FOLDER,
    ledger_name="experiment-1",
    protocol_path=f"research/{FOLDER}/PROTOCOL.md",
    periods=(
        Period(c.PERIOD_DISCOVERY, date(2024, 1, 1), date(2026, 10, 9), decisive=False),
        Period(c.PERIOD_CHALLENGE, date(2019, 1, 1), date(2023, 12, 31), decisive=True),
    ),
    policies=POLICIES,
    control_trials=("30", "31"),  # C1 random timing, C2 opposite condition
    stats=StatisticsTerms(
        seed=SEED,
        resamples=10_000,
        lower_bound_index=62,
        control_runs=10_000,
        control_percentile=0.95,
        mc_repeats=20,
        tax_rate=0.312,
        loss_cap=10_000.0,
    ),  # fmt: skip
    hypotheses=8,
)
