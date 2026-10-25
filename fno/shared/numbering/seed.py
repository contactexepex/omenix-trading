"""The registry seed (story O12): one `existing` row for each numbered file or heading not registered yet, then the
seed pin rewritten.

Run once, on the merged tree when O12 merges, so the files already on `main` are history and not clashes. A later run
changes `fno/numbering/seed_pins.json`, a code file (lane 1), so the judge sees every row it adds.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from fno.shared.numbering.blocks import LEDGER_TRIAL, ledger_trials, seed_blocks
from fno.shared.numbering.categories import CATEGORIES
from fno.shared.numbering.numbered_items import numbered_items
from fno.shared.numbering.registry import SEEDED, Row, append_row, read_rows
from fno.shared.numbering.seed_pin import read_pins, seeded_digest, write_pins


def seed_registries(root: Path) -> int:
    """Appends the missing seeded rows to every registry; returns how many were added."""
    added = 0
    for category in CATEGORIES.values():
        path = root / category.registry
        registered = Counter(category.key(row.number, row.name) for row in read_rows(path))
        for item in numbered_items(root, category):
            key = next((k for k in category.keys_for_file(item.number, item.name) if registered[k]), None)
            if key is not None:
                registered[key] -= 1
                continue
            append_row(path, Row(item.number, item.name, SEEDED))
            added += 1
    added += _seed_ledger_trials(root)
    series = [*CATEGORIES.values(), LEDGER_TRIAL]
    write_pins(root, {**read_pins(root), **{s.name: seeded_digest(read_rows(root / s.registry)) for s in series}})
    return added


def _seed_ledger_trials(root: Path) -> int:
    """Story O12e: the ledger's trials no block covers yet, one history block per run of one experiment."""
    path = root / LEDGER_TRIAL.registry
    blocks = seed_blocks(ledger_trials(root), read_rows(path))
    for block in blocks:
        append_row(path, Row(block.text, block.name, SEEDED))
    return len(blocks)
