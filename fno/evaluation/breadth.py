"""BR1's breadth protocol as a protocol definition (story BR1a): `research/breadth/PROTOCOL.md`, its required items
and its own freeze record. A BR1 claim decides no money, so the real-money gate (story RM1) is not frozen with it.
Only the composition root (`wiring.py`) passes this definition to the freezer and the checks."""

from __future__ import annotations

from .definition import ProtocolDefinition

BREADTH_PROTOCOL_FILE = "research/breadth/PROTOCOL.md"

BREADTH_ITEMS = {
    "universe": "the F&O underlyings scored, and how names enter and leave",
    "target": "T1: the move is at least the ATM-straddle implied daily move; spot and calendar",
    "outcome_exclusion": "the corporate-action screen, outcome-side only, counts disclosed",
    "forecast_time": "end of day, committed before 09:15 IST; 14:30 descriptive",
    "families": "rule, hybrid and AI, and the names each is scored on",
    "baselines": "market, trail60 and cal60, with their formulas",
    "primary_baseline_rule": "the single primary baseline, set by study 1",
    "claim_meaning": "the only confirmatory claim: family F beats the primary baseline on T1, end of day",
    "confirmatory_family": "K = 3, one member per family; what is descriptive only",
    "test": "the daily series, the test, Holm and the minimum blocks",
    "minimum_effect": "the planning effect behind the look counts",
    "looks": "the two look counts and the rate, set together by study 3",
    "futility": "the futility rule at look 1, as study 3 left it",
    "null_size_check": "study 3, its limits, its fallback and its result",
    "regime_gate": "study 2 and its result",
    "descriptive_reports": "what is reported but never tested",
    "reporting": "every member at every look, losers too, per protocol version",
    "frozen_files": "the files the freeze hashes: this protocol, the panel, baseline and scoring code, rules, subset",
}

BREADTH = ProtocolDefinition(
    protocol_file=BREADTH_PROTOCOL_FILE,
    required_items=BREADTH_ITEMS,
    freeze_template="research/breadth/FREEZE_v{version}.md",
    record_title="Breadth protocol freeze record",
    record_rule="story BR1a, criterion 2",
    ledger_description="Breadth protocol v{version}: BR1's T1 claim against the primary baseline (story BR1a)",
    ledger_experiment="breadth-protocol-v{version}",
    requires_gate=False,
)
