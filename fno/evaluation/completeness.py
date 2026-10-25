"""The protocol's completeness check (story S1, criterion 2). Two questions, asked separately:
- **complete**: every required item is present once, with a value or an exact rule, a status, a reason and an
  evidence label; "to be decided" and its kin appear nowhere in the document;
- **decided**: every item's status says the owner decided it, and when, and no value still carries the "(set at the
  freeze)" marker (a number the owner fixes on the freeze day, judge 196). Only a complete and decided protocol can be
  frozen. A draft of proposals can be complete without being decided.
The same check serves the real-money gate (story RM1): it passes its own required items and has no version line."""

from __future__ import annotations

import re

from .protocol import DECIDED, EVIDENCE_LABELS, FIELDS, PROPOSAL, REQUIRED_ITEMS, Protocol

SET_AT_FREEZE = "(set at the freeze)"
UNDECIDED_WORDS = re.compile(r"\b(to be decided|to be determined|tbd|tbc|to decide later|undecided)\b", re.IGNORECASE)


def _item_problems(protocol: Protocol, required: dict[str, str]) -> list[str]:
    problems = []
    for key in required:
        item = protocol.items.get(key)
        if item is None:
            problems.append(f"{key}: missing ({required[key]})")
            continue
        empty = [name for name in FIELDS if not item.fields.get(name)]
        if empty:
            problems.append(f"{key}: no {', '.join(empty)}")
        status, evidence = item.fields.get("Status", ""), item.fields.get("Evidence", "")
        if status and status != PROPOSAL and not DECIDED.match(status):
            problems.append(f"{key}: status must be {PROPOSAL!r} or 'decided by the owner on YYYY-MM-DD'")
        if evidence and evidence not in EVIDENCE_LABELS:
            problems.append(f"{key}: evidence must be one of {', '.join(EVIDENCE_LABELS)}")
    return problems


def completeness_problems(
    text: str, protocol: Protocol, required: dict[str, str] = REQUIRED_ITEMS, versioned: bool = True
) -> list[str]:
    """Why the document is not complete; empty when it is. `versioned` asks for the 'Protocol version' line."""
    problems = [] if protocol.version or not versioned else ["no 'Protocol version: <n>' line"]
    problems += [f"{key}: appears more than once" for key in protocol.duplicates]
    problems += [f"unknown item {key!r}" for key in protocol.items if key not in required]
    problems += _item_problems(protocol, required)
    for number, line in enumerate(text.splitlines(), start=1):
        found = UNDECIDED_WORDS.search(line)
        if found:
            problems.append(f"line {number}: {found.group(0)!r} is not a value or a rule")
    return problems


def undecided_items(protocol: Protocol) -> list[str]:
    """Items the owner has not decided yet, or whose value waits for the freeze day: a protocol with any is a draft and
    cannot be frozen."""
    return [key for key, item in protocol.items.items()
            if not DECIDED.match(item.fields.get("Status", "")) or SET_AT_FREEZE in item.value]  # fmt: skip
