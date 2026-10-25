"""The number check (story O12): every numbered file or heading has its registry row, and no number is used twice.

Seeded history (session `existing`) may hold a number twice; nothing claimed after the seed may. The seeded rows
must equal their pinned SHA-256 (`seed_pin.py`), so no seeded row can be added later to hide a clash.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from fno.shared.numbering.blocks import LEDGER_TRIAL, BlockSeries, block_findings, ledger_ids
from fno.shared.numbering.categories import CATEGORIES, AddendumCategory, Category
from fno.shared.numbering.numbered_items import NumberedItem, misnamed_files, numbered_items
from fno.shared.numbering.registry import Row, read_rows, valid_stamp
from fno.shared.numbering.seed_pin import PINS, read_pins, seeded_digest

EMPTY_SEED = seeded_digest([])  # a category with no pin has no seeded history

NO_ROW = "{where}: number {number} has no row in {registry}"
SHARED = "{registry}: number {number} is used {count} times ({names}); only seeded history may repeat a number"
BAD_ROW = "{registry}: row {number},{name}: {reason}"
SEED_CHANGED = "{registry}: the seeded rows differ from their pin in {pins}; the seed is history only"
MISNAMED = "{where}: not a {prefix}_<n>_<slug>.md name, so its number cannot be checked"


def check_numbers(root: Path) -> list[str]:
    """One finding line per problem, across every category; empty when clean."""
    pins = read_pins(root)
    files = [line for category in CATEGORIES.values() for line in _check_category(root, category, pins)]
    return files + _check_blocks(root, LEDGER_TRIAL, pins)


def _check_category(root: Path, category: Category, pins: dict[str, str]) -> list[str]:
    try:
        rows = read_rows(root / category.registry)
    except ValueError as malformed:
        return [f"{category.registry}: {malformed}"]
    items = numbered_items(root, category)
    misnamed = [] if isinstance(category, AddendumCategory) else misnamed_files(root, category)
    return [
        *[MISNAMED.format(where=where, prefix=category.prefix) for where in misnamed],
        *_seed_changed(category, rows, pins),
        *_bad_rows(category, rows),
        *_missing_rows(category, rows, items),
        *_shared_numbers(category, rows, items),
    ]


def _check_blocks(root: Path, series: BlockSeries, pins: dict[str, str]) -> list[str]:
    """Story O12e: the ledger's trial ids against their claimed blocks."""
    try:
        rows = read_rows(root / series.registry)
    except ValueError as malformed:
        return [f"{series.registry}: {malformed}"]
    return [*_seed_changed(series, rows, pins), *_bad_rows(series, rows), *block_findings(rows, ledger_ids(root))]


def _seed_changed(category: Category | BlockSeries, rows: list[Row], pins: dict[str, str]) -> list[str]:
    if pins.get(category.name, EMPTY_SEED) == seeded_digest(rows):
        return []
    return [SEED_CHANGED.format(registry=category.registry, pins=PINS)]


def _bad_rows(category: Category | BlockSeries, rows: list[Row]) -> list[str]:
    found = []
    for row in rows:
        reason = _row_problem(category, row)
        if reason:
            found.append(BAD_ROW.format(registry=category.registry, number=row.number, name=row.name, reason=reason))
    return found


def _row_problem(category: Category | BlockSeries, row: Row) -> str | None:
    if not category.valid_number(row.number):
        return "number is not of this category's form"
    if not row.name:
        return "no name"
    if row.seeded:
        return "a seeded row has no time" if row.claimed_at_utc else None
    if not row.session:
        return "no claiming session"
    return None if valid_stamp(row.claimed_at_utc) else "claimed_at_utc is not YYYY-MM-DDTHH:MM:SSZ"


def _missing_rows(category: Category, rows: list[Row], items: list[NumberedItem]) -> list[str]:
    registered = {category.key(row.number, row.name) for row in rows}
    missing = {
        (i.where, i.number) for i in items if not any(k in registered for k in category.keys_for_file(i.number, i.name))
    }
    return [NO_ROW.format(where=w, number=n, registry=category.registry) for w, n in sorted(missing, key=_where_order)]


def _shared_numbers(category: Category, rows: list[Row], items: list[NumberedItem]) -> list[str]:
    """A number held by two rows, or by more files or headings than it has seeded rows."""
    row_count = Counter(row.number for row in rows)
    seeded_count = Counter(row.number for row in rows if row.seeded)
    item_count = Counter(item.number for item in items)
    found = []
    for number in sorted(set(row_count) | set(item_count), key=_order):
        uses = max(row_count[number], item_count[number])
        if uses > 1 and seeded_count[number] < uses:
            names = sorted({row.name for row in rows if row.number == number} | _item_names(items, number))
            found.append(SHARED.format(registry=category.registry, number=number, count=uses, names=", ".join(names)))
    return found


def _item_names(items: list[NumberedItem], number: str) -> set[str]:
    return {item.name for item in items if item.number == number}


def _where_order(missing: tuple[str, str]) -> tuple:
    return missing[0], _order(missing[1])


def _order(number: str) -> tuple[int, ...]:
    return tuple(int(part) if part.isdigit() else 0 for part in number.split("."))
