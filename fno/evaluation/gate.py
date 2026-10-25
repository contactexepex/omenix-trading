"""The real-money gate as a document (story RM1): `research/evaluation/REAL_MONEY_GATE.md`, in the protocol's item
format, with no version line of its own: it is versioned and frozen with the evaluation protocol (S1), whose
`frozen_files` lists it. The freeze refuses while the gate is not listed, not complete or not decided by the owner.

Nothing here reads the gate to act: it decides only when a strategy version may be put to the owner, who places every
real order by hand."""

from __future__ import annotations

from .completeness import completeness_problems, undecided_items
from .protocol import parse_protocol

GATE_FILE = "research/evaluation/REAL_MONEY_GATE.md"

GATE_ITEMS = {
    "scope": "what the gate decides: eligibility to put to the owner, never an order (design v2 8.3)",
    "paper_evidence": "condition 1: the paper record's sample, lower bounds and whole-period net (8.3)",
    "index_benchmark": "condition 2: beats the index fund after tax (8.3, decision 168)",
    "loss_caps": "condition 3: losses within their caps, in the record and the crash replays (8.3)",
    "fill_honesty": "condition 4: paper fills not kinder than the market (8.3)",
    "selection_adjustment": "condition 5: the second untouched forward period (8.3, decision 8 amended)",
    "real_cap_fit": "condition 6: the trade fits the real cap; SEBI and tax re-checked (8.3)",
    "owner_approval": "condition 7: the owner's written yes (8.3)",
    "real_test_account": "the real test's account, cap and lot (8.4)",
    "real_test_sample": "the real test's length (8.4)",
    "real_test_pass": "the paired real-versus-paper pass rule (8.4, decision 8 amended)",
    "real_test_stops": "the real test's stops (8.4)",
}


def gate_problems(text: str, decided: bool) -> list[str]:
    """Why the gate is not complete (or, with `decided`, not decided by the owner); empty when it is."""
    gate = parse_protocol(text)
    problems = completeness_problems(text, gate, GATE_ITEMS, versioned=False)
    undecided = undecided_items(gate) if decided else []
    return problems + ([f"not decided by the owner: {', '.join(undecided)}"] if undecided else [])
