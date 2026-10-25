"""The evaluation protocol as a document (story S1): `research/evaluation/PROTOCOL.md`. It has a version line and one
block per item, in this form:

    ### `common_start` Common start date
    - **Value:** the exact value or rule (continuation lines indented by two spaces)
    - **Status:** proposal, owner decides | decided by the owner on YYYY-MM-DD
    - **Reason:** why this value
    - **Evidence:** strong evidence | some evidence | reasoning only

The items S1 requires are listed here. Story S1, criterion 2: each item needs a value or an exact rule."""

from __future__ import annotations

import re
from dataclasses import dataclass

PROTOCOL_FILE = "research/evaluation/PROTOCOL.md"
FIELDS = ("Value", "Status", "Reason", "Evidence")
EVIDENCE_LABELS = ("strong evidence", "some evidence", "reasoning only")
PROPOSAL = "proposal, owner decides"
DECIDED = re.compile(r"^decided by the owner on \d{4}-\d{2}-\d{2}$")
VERSION_LINE = re.compile(r"^Protocol version: ([1-9][0-9]*)$", re.MULTILINE)
ITEM_HEADING = re.compile(r"^### `([a-z_]+)` (.+)$")
FIELD_LINE = re.compile(r"^- \*\*(\w+):\*\* ?(.*)$")
CONTINUATION = "  "

REQUIRED_ITEMS = {
    "common_start": "the common start date, or the rule that sets it (design 12.6)",
    "pilot_evidence": "what counts as pilot evidence, kept apart from head-to-head results (design 12.6)",
    "timetable": "the daily timetable times (story E3, design 13.5)",
    "segments": "the evaluation segment rules (story D6)",
    "primary_metric": "the primary verdict's measure (design 12.8)",
    "scoreboard_a_standardisation": "how scoreboard A's matched decisions are standardised (story S3)",
    "uncertainty_criterion": "the uncertainty criterion for any promotion or combination, with block length and seed",
    "paper_gate": "the minimum paper sample before any real-money discussion (design 6, story E6)",
    "strategy_review_rule": "the per-strategy keep, pause or retire rule at a review (story E6)",
    "catastrophic_loss_strategy": "the catastrophic-loss rule per strategy (design 12.8)",
    "catastrophic_loss_book": "the catastrophic-loss rule per book (design 12.8)",
    "immediate_pauses": "the only reasons to pause before a scheduled review (design 12.8)",
    "review_dates": "the scheduled review dates (design 12.8)",
    "ai_cost_allocation": "the AI plan-cost allocation formula (story F8, design 13.6)",
    "role_value_schedule": "the role-value evaluation and ablation schedule (story F9, design 13.6)",
    "role_value_minimum_sample": "the role-value minimum sample and decision rule (story F9)",
    "reporting_per_version": "how results are reported per protocol version (story S1, criterion 3)",
    "do_nothing_benchmark": "the do-nothing comparison after tax, a gate before real money (story S6)",
    "scorecard_measures": "net without the best trade, profit factor, drawdown and worst day (story S6)",
    "t_check": "the t-based check beside the bootstrap, a printed warning only (story S6)",
    "missed_runs": "missed desk runs on scoreboards A and B, with the miss cap (story S6)",
    "random_control": "the random-strategy control, descriptive (story S6)",
    "frozen_files": "the files and settings the freeze hashes (scoring code, timetable, allocation formula)",
}


@dataclass(frozen=True)
class Item:
    key: str
    title: str
    fields: dict[str, str]

    @property
    def value(self) -> str:
        return self.fields.get("Value", "")


@dataclass(frozen=True)
class Protocol:
    version: int | None
    items: dict[str, Item]
    duplicates: tuple[str, ...] = ()  # item keys that appear more than once


def _blocks(lines: list[str]):
    """(key, title, body lines) of each item block."""
    current = None
    for line in lines:
        heading = ITEM_HEADING.match(line)
        if heading:
            if current:
                yield current
            current = (heading.group(1), heading.group(2), [])
        elif line.startswith("#"):
            if current:
                yield current
            current = None
        elif current:
            current[2].append(line)
    if current:
        yield current


def _fields(body: list[str]) -> dict[str, str]:
    fields: dict[str, list[str]] = {}
    name = None
    for line in body:
        match = FIELD_LINE.match(line)
        if match:
            name = match.group(1)
            fields.setdefault(name, []).append(match.group(2))
        elif name and line.startswith(CONTINUATION) and line.strip():
            fields[name].append(line.strip())
        elif not line.strip():
            name = None
    return {key: " ".join(parts).strip() for key, parts in fields.items()}


def parse_protocol(text: str) -> Protocol:
    version = VERSION_LINE.search(text)
    items: dict[str, Item] = {}
    duplicates = []
    for key, title, body in _blocks(text.splitlines()):
        if key in items:
            duplicates.append(key)
        items.setdefault(key, Item(key, title, _fields(body)))
    return Protocol(int(version.group(1)) if version else None, items, tuple(duplicates))
